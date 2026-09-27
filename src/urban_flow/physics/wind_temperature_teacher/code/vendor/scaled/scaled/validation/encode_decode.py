import torch
import torch.distributed as dist
import torch.nn.functional as F
from scaled.model.autoencoders.autoencoder3dv1 import AutoencoderKL
# import numpy as _np
import h5py
import os
import numpy as np
import shutil
import math

def cleanup_distributed():
    if dist.is_available() and dist.is_initialized():
        dist.barrier()
        dist.destroy_process_group()

def is_main(rank: int) -> bool:
    return rank == 0

def barrier():
    if dist.is_available() and dist.is_initialized():
        dist.barrier()

def tile_iterator(n_rows: int, n_cols: int, rank: int, world_size: int):
    """按线性序号切分 tiles 给各 rank。"""
    total = n_rows * n_cols
    for linear in range(rank, total, world_size):
        i = linear // n_cols
        j = linear % n_cols
        yield i, j

def tile_owner(i, j, n_cols, world_size):
    return ((i * n_cols) + j) % world_size

# rank0 侧：创建 HDF5 文件与数据集（只创建，不驻留大数组）
def rank0_open_h5(h5_path, shape, chunks, dtype=np.float16, compression="gzip", compression_opts=4):
    # shape = (N=1, C=4, D_lat, H_lat, W_lat)
    # chunks = (1, 4, D_lat, tile_lat, tile_lat)  或按需要调整
    f = h5py.File(h5_path, "w")  # 单写者
    dset0  = f.create_dataset("latent0",  shape=shape, chunks=chunks, dtype=dtype,
                              compression=compression, compression_opts=compression_opts)
    dsetbg = f.create_dataset("latentbg", shape=shape, chunks=chunks, dtype=dtype,
                              compression=compression, compression_opts=compression_opts)
    return f, dset0, dsetbg

# -----------------------------
# 编码/解码/推理（DDP 并行，CPU 常驻）
# -----------------------------
class DataPreprocessDDP:
    """
    - encode_distributed_with_halo: 将 (data_0, data_bg) 以 tile+halo 并行送 VAE.encode，
      回填 latent 核心区，分片落盘，rank0 组装并返回 (latent_0, latent_bg)（CPU）。
    - decode_single_visualize_distributed: 将 latent 以 tile+halo 并行送 VAE.decode，
      仅保留核心 tile_out×tile_out，分片落盘，rank0 汇总可视化保存。
    """
    def __init__(self, 
                 compression_model, 
                 scale_ratio,
                 geometry_path,
                 work_dir_path,
                 shape,
                 device,
                 rank: int, 
                 world_size: int):
        self.scale = scale_ratio
        self.compression_model = compression_model.to(device).eval()
        self.shape = shape
        self.device = device
        self.rank = rank
        self.world_size = world_size
        self.work_dir = work_dir_path
        self.initial_latent_path = os.path.join(work_dir_path,'initial_latent')
        self.initial_geometry_path = os.path.join(work_dir_path,'initial_geometry_path')
        self.shard_encode_dir = os.path.join(work_dir_path,'shared_encoded_tiles_dir')
        self.shard_geometry_dir = os.path.join(work_dir_path,'shared_geometry_tiles_dir')
        self.shared_decoded_tiles_dir = os.path.join(work_dir_path,'shared_decoded_tiles_dir')
        self.saved_decoded_tiles_dir = os.path.join(work_dir_path,'saved_decoded_tiles_dir')
        self.decode_result_dir = os.path.join(work_dir_path,'decode_result_dir')
        self.geometry_path = geometry_path
        self.shape = shape
        self.scale = 4
        self.make_dirs()

    def make_dirs(self,):
        os.makedirs(self.shard_geometry_dir,exist_ok=True)
        os.makedirs(self.shard_encode_dir,exist_ok=True)
        os.makedirs(self.initial_latent_path,exist_ok=True)
        os.makedirs(self.initial_geometry_path,exist_ok=True)
        os.makedirs(self.shared_decoded_tiles_dir,exist_ok=True)
        os.makedirs(self.decode_result_dir,exist_ok=True)
        os.makedirs(self.saved_decoded_tiles_dir,exist_ok=True)


    def make_data_bg(self,geometry):
        """构造 data_0 / data_bg；data_bg 在建筑为0，其余为1。输出 [1,3,D,H,W]（CPU）。"""
        d, h, w = self.geometry.shape
        geometry[0] = 1
        data_bg = torch.ones((1, 3, d, h, w), dtype=torch.float32)  # CPU
        data_bg[:, :, self.geometry.bool()] = 0.0
        data_0 = torch.zeros((1, 3, d, h, w), dtype=torch.float32)  # CPU
        return data_0, data_bg

    def preprocess_geometry_into_tiles(self,tile_hw=256, halo=8):
        if is_main(self.rank):
            n_h = self.shape[1]//tile_hw
            n_w = self.shape[2]//tile_hw
            geometry = np.load(self.geometry_path)
            geometry[0] = 1
            geometry = geometry.astype(bool)
            for i in range(n_h):
                for j in range(n_w):
                    print(f'processing {i}_{j} tiles')
                    hs = i * tile_hw
                    ws = j * tile_hw
                    he = hs + tile_hw
                    we = ws + tile_hw
                    y0 = max(hs - halo, 0)
                    x0 = max(ws - halo, 0)
                    y1 = min(he + halo, self.shape[1])
                    x1 = min(we + halo, self.shape[2])
                    geo_small = geometry[:, y0:y1, x0:x1]  # bool/float32 都行
                    geo_small = torch.from_numpy(geo_small).to(float)
                    need_h = tile_hw + 2 * halo
                    need_w = tile_hw + 2 * halo
                    cur_h = geo_small.shape[1]
                    cur_w = geo_small.shape[2]
                    pad_top    = max(0, halo - (hs - y0))
                    pad_left   = max(0, halo - (ws - x0))
                    pad_bottom = max(0, (he + halo) - y1)
                    pad_right  = max(0, (we + halo) - x1)
                    # 对 H/W 维做 reflect pad（只 pad 小窗，不 pad 整图）
                    # F.pad 输入形状要 [N,C,H,W]，这里把 D 当 batch 维处理，再还原
                    geo_small_4d = geo_small.unsqueeze(1)              # [D,1,h',w']
                    geo_pad = F.pad(
                        geo_small_4d,
                        (pad_left, pad_right, pad_top, pad_bottom),    # (W_left,W_right,H_top,H_bottom)
                        mode="replicate"
                    ).squeeze(1)                                       # [D, need_h, need_w]
                    # bg_mask = (~geo_pad.bool()).to(torch.bool)      # [D,need_h,need_w], 背景=1
                    geo_pad = geo_pad.numpy().astype(bool)
                    geo_pad = np.packbits(geo_pad)
                    np.save(os.path.join(self.initial_geometry_path,f"bgmask_{i}_{j}.npy"),geo_pad)
                    # subbg_cpu = bg_mask.unsqueeze(0).unsqueeze(0).expand(1, 3, geo_pad.shape[0], need_h, need_w).contiguous()
                    # sub0_cpu  = torch.zeros_like(subbg_cpu)
                    # torch.save(bg_mask,os.path.join(self.initial_geometry_path,f"bgmask_{i}_{j}.pt"))
                    # torch.save(sub0_cpu,os.path.join(self.initial_geometry_path,f"sub0_{i}_{j}.pt"))
        barrier()

    def get_primitive_variable(self,i,j):
        geo_pad = np.load(os.path.join(self.initial_geometry_path,f"bgmask_{i}_{j}.npy"))
        geo_pad = np.unpackbits(geo_pad).reshape((64, 272, 272))
        print(geo_pad.shape)
        geo_pad = torch.from_numpy(geo_pad)
        bg_mask = (~geo_pad.bool()).to(torch.float32)
        subbg = bg_mask.unsqueeze(0).unsqueeze(0).expand(1, 3, 64, 272, 272).contiguous().to(self.device)
        sublatent = torch.zeros_like(subbg).to(self.device)

        # sub0 = torch.load(os.path.join(self.initial_geometry_path,f"sub0_{i}_{j}.pt")).to(self.device)
        return subbg,sublatent

    def encode_distributed_with_halo(self, tile_hw=256, halo=8):
        """
        多卡并行（DDP）：每个 rank 处理一部分 tiles。
        - CPU 侧对 H/W 做 ReplicationPad3d
        - encode 后在 latent 侧裁掉 halo_lat，仅回填核心
        - 每 tile 写分片，rank0 汇总返回
        """
        # --- DDP init ---
        # self.rank, self.world_size, self.local_rank, self.device = setup_distributed()

        torch.backends.cudnn.benchmark = True
        self.compression_model = self.compression_model.to(self.device).eval()

        print(f"[rank {self.rank}] start encode on {self.device}")
        halo_lat = halo // self.scale

        d, h, w = self.shape
        # assert h % tile_hw == 0 and w % tile_hw == 0, "H/W 必须能被 tile_hw 整除。"
        H_lat, W_lat = h // self.scale, w // self.scale
        tile_lat = tile_hw // self.scale

        n_rows = h // tile_hw
        n_cols = w // tile_hw

        # 本 rank 负责的 tiles
        for i, j in tile_iterator(n_rows, n_cols, self.rank, self.world_size):
            print(f'rank:{self.rank} processing {i} {j} tiles')
            subbg,sub0 = self.get_primitive_variable(i,j)
            with torch.inference_mode(), torch.amp.autocast(device_type="cuda", dtype=torch.float32):
                lat0  = self.compression_model.encode(sub0)
                latbg = self.compression_model.encode(subbg)
            # 裁核心（GPU -> CPU）
            hs_l = halo_lat
            he_l = hs_l + tile_lat
            ws_l = halo_lat
            we_l = ws_l + tile_lat
            lat0_core  = lat0[:, :, :, hs_l:he_l, ws_l:we_l].to("cpu", non_blocking=False)
            latbg_core = latbg[:, :, :, hs_l:he_l, ws_l:we_l].to("cpu", non_blocking=False)
            latent_0_core_path = os.path.join(self.shard_encode_dir, f'{i}_{j}_latent0.pt')
            latent_bg_core_path = os.path.join(self.shard_encode_dir, f'{i}_{j}_latentbg.pt')
            torch.save(lat0_core,latent_0_core_path)
            torch.save(latbg_core,latent_bg_core_path)
        barrier()
        if is_main(self.rank):
            print("[rank 0] all shard files saved. start stitching...")
        if is_main(self.rank):
            latent0  = torch.zeros((1, 4, d // self.scale, H_lat, W_lat), dtype=torch.float32)
            latentbg = torch.zeros_like(latent0)
            for i in range(n_rows):
                for j in range(n_cols):
                    print(f'process tiles {i} {j}')
                    # for r in range(self.world_size):
                    p0  = os.path.join(self.shard_encode_dir, f'{i}_{j}_latent0.pt')
                    pbg = os.path.join(self.shard_encode_dir, f'{i}_{j}_latentbg.pt')
                    # if p0.exists() and pbg.exists():
                    lat0_core  = torch.load(p0)
                    latbg_core = torch.load(pbg)
                    # raise RuntimeError(f"Missing encode tile ({i},{j})")
                    hi = i * tile_lat
                    hj = j * tile_lat
                    latent0[:, :, :, hi:hi + tile_lat, hj:hj + tile_lat]  = lat0_core
                    latentbg[:, :, :, hi:hi + tile_lat, hj:hj + tile_lat] = latbg_core
            torch.save(latent0,os.path.join(self.initial_latent_path,'latent0.pt'))
            torch.save(latentbg,os.path.join(self.initial_latent_path,'latentbg.pt'))
        barrier()

    @torch.no_grad()
    def decode_single_visualize_distributed(self, latent_cpu: torch.Tensor, t: int,
                                            tile_out=256, halo_lat=2, scale=4):
        """
        latent_cpu: [1,4,D,H_lat,W_lat]（CPU）
        latent 侧 pad=halo_lat，按 tile_lat=tile_out//scale 网格切块，
        decode 后插值到 expected_hw，再居中裁成 tile_out×tile_out 核心分片写盘；
        rank0 汇总整幅到 CPU 并可视化保存一张切片图。
        """
        # if is_main(self.rank):
        #     shutil.rmtree(self.shared_decoded_tiles_dir, ignore_errors=True)
        save_tiles_dir  = os.path.join(self.saved_decoded_tiles_dir,f'{t:04d}')
        os.makedirs(save_tiles_dir,exist_ok=True)
        barrier()
        device = self.device
        B, C_lat, D_lat, H_lat, W_lat = latent_cpu.shape
        assert tile_out % scale == 0
        tile_lat = tile_out // scale

        H = H_lat * scale
        W = W_lat * scale
        expected_hw = scale * (tile_lat + 2 * halo_lat)

        if halo_lat > 0:
            latent_pad = F.pad(latent_cpu, (halo_lat, halo_lat, halo_lat, halo_lat, 0, 0),
                               mode="reflect")
        else:
            latent_pad = latent_cpu
        H_lat_pad = H_lat + 2 * halo_lat
        W_lat_pad = W_lat + 2 * halo_lat

        n_rows = math.ceil(H_lat / tile_lat)
        n_cols = math.ceil(W_lat / tile_lat)

        for i, j in tile_iterator(n_rows, n_cols, self.rank, self.world_size):
            print(f'rank {self.rank} is processing {i}th {j}th')
            y0_lat = i * tile_lat
            x0_lat = j * tile_lat
            y1_lat = y0_lat + tile_lat + 2 * halo_lat
            x1_lat = x0_lat + tile_lat + 2 * halo_lat
            y0_lat = max(0, min(y0_lat, H_lat_pad))
            x0_lat = max(0, min(x0_lat, W_lat_pad))
            y1_lat = max(0, min(y1_lat, H_lat_pad))
            x1_lat = max(0, min(x1_lat, W_lat_pad))
            sub_lat = latent_pad[:, :, :3, y0_lat:y1_lat, x0_lat:x1_lat].pin_memory().to(device, non_blocking=True)
            with torch.amp.autocast(device_type="cuda", dtype=torch.float32):
                dec = self.compression_model.decode(sub_lat)  # [B,3,D,H_dec,W_dec]
            # if dec.shape[-2] != expected_hw or dec.shape[-1] != expected_hw:
            #     dec = F.interpolate(dec, size=(expected_hw, expected_hw),mode="trilinear", align_corners=False)
            total_trim = expected_hw - tile_out
            top_trim = total_trim // 2
            left_trim = total_trim // 2
            bottom_trim = total_trim - top_trim
            right_trim = total_trim - left_trim
            core = dec[:, :, :, top_trim:expected_hw - bottom_trim,
                       left_trim:expected_hw - right_trim].to("cpu", non_blocking=False)
            Y0 = i * tile_out
            X0 = j * tile_out
            Y1 = min(Y0 + tile_out, H)
            X1 = min(X0 + tile_out, W)
            core = core[:, :, :, :Y1 - Y0, :X1 - X0]
            tiles_path = os.path.join(save_tiles_dir,f'{i}_{j}.pt')
            result = core[0,0,5].to(torch.float16)
            print(result.shape)
            torch.save(result,tiles_path)
        barrier()
        # if is_main(self.rank):
        #     result = torch.zeros(( H, W), dtype=torch.float32)
        #     for i in range(n_rows):
        #         for j in range(n_cols):
        #             tiles_path = os.path.join(self.shared_decoded_tiles_dir,f'{i}_{j}.pth')
        #             if not os.path.exists(tiles_path):
        #                 raise ValueError(f'did not find file {tiles_path}')
        #             core = torch.load(tiles_path)
        #             Y0 = i * tile_out
        #             X0 = j * tile_out
        #             Y1 = min(Y0 + tile_out, H)
        #             X1 = min(X0 + tile_out, W)
        #             result[ Y0:Y1, X0:X1] = core[0]
        #     torch.save(result.cpu().to(torch.float16),os.path.join(self.decode_result_dir, f'{t:05d}.pt'))
        # barrier()


    # @torch.no_grad()
    # def decode_single_visualize_distributed(self, 
    #                                         latent_cpu: torch.Tensor, 
    #                                         t: int,
    #                                         tile_out=256, 
    #                                         halo_lat=2, 
    #                                         scale=4):
    #     """
    #     latent_cpu: [1,4,D,H_lat,W_lat]（CPU）
    #     latent 侧 pad=halo_lat，按 tile_lat=tile_out//scale 网格切块，
    #     decode 后插值到 expected_hw，再居中裁成 tile_out×tile_out 核心分片写盘；
    #     rank0 汇总整幅到 CPU 并可视化保存一张切片图。
    #     """
    #     if is_main(self.rank):
    #         # shutil.rmtree(self.shared_decoded_tiles_dir, ignore_errors=True)
    #         os.makedirs(self.shared_decoded_tiles_dir,exist_ok=True)
    #     barrier()
    #     device = self.device
    #     B, C_lat, D_lat, H_lat, W_lat = latent_cpu.shape
    #     assert tile_out % scale == 0
    #     tile_lat = tile_out // scale

    #     H = H_lat * scale
    #     W = W_lat * scale
    #     expected_hw = scale * (tile_lat + 2 * halo_lat)

    #     if halo_lat > 0:
    #         latent_pad = F.pad(latent_cpu, (halo_lat, halo_lat, halo_lat, halo_lat, 0, 0),
    #                            mode="reflect")
    #     else:
    #         latent_pad = latent_cpu
    #     H_lat_pad = H_lat + 2 * halo_lat
    #     W_lat_pad = W_lat + 2 * halo_lat

    #     n_rows = math.ceil(H_lat / tile_lat)
    #     n_cols = math.ceil(W_lat / tile_lat)

    #     for i, j in tile_iterator(n_rows, n_cols, self.rank, self.world_size):
    #         print(f'rank {self.rank} is processing {i}th {j}th')
    #         y0_lat = i * tile_lat
    #         x0_lat = j * tile_lat
    #         y1_lat = y0_lat + tile_lat + 2 * halo_lat
    #         x1_lat = x0_lat + tile_lat + 2 * halo_lat
    #         y0_lat = max(0, min(y0_lat, H_lat_pad))
    #         x0_lat = max(0, min(x0_lat, W_lat_pad))
    #         y1_lat = max(0, min(y1_lat, H_lat_pad))
    #         x1_lat = max(0, min(x1_lat, W_lat_pad))
    #         sub_lat = latent_pad[:, :, :3, y0_lat:y1_lat, x0_lat:x1_lat].pin_memory().to(device, non_blocking=True)
    #         with torch.amp.autocast(device_type="cuda", dtype=torch.float32):
    #             dec = self.compression_model.decode(sub_lat)  # [B,3,D,H_dec,W_dec]
    #         # if dec.shape[-2] != expected_hw or dec.shape[-1] != expected_hw:
    #         #     dec = F.interpolate(dec, size=(expected_hw, expected_hw),mode="trilinear", align_corners=False)
    #         total_trim = expected_hw - tile_out
    #         top_trim = total_trim // 2
    #         left_trim = total_trim // 2
    #         bottom_trim = total_trim - top_trim
    #         right_trim = total_trim - left_trim
    #         core = dec[:, :, :, top_trim:expected_hw - bottom_trim,
    #                    left_trim:expected_hw - right_trim].to("cpu", non_blocking=False)
    #         Y0 = i * tile_out
    #         X0 = j * tile_out
    #         Y1 = min(Y0 + tile_out, H)
    #         X1 = min(X0 + tile_out, W)
    #         core = core[:, :, :, :Y1 - Y0, :X1 - X0]
    #         tiles_path = os.path.join(self.shared_decoded_tiles_dir,f'{i}_{j}.pth')
    #         torch.save(core[0,:,5],tiles_path)

        # barrier()
        # if is_main(self.rank):
        #     result = torch.zeros(( H, W), dtype=torch.float32)
        #     for i in range(n_rows):
        #         for j in range(n_cols):
        #             tiles_path = os.path.join(self.shared_decoded_tiles_dir,f'{i}_{j}.pth')
        #             if not os.path.exists(tiles_path):
        #                 raise ValueError(f'did not find file {tiles_path}')
        #             core = torch.load(tiles_path)
        #             Y0 = i * tile_out
        #             X0 = j * tile_out
        #             Y1 = min(Y0 + tile_out, H)
        #             X1 = min(X0 + tile_out, W)
        #             result[ Y0:Y1, X0:X1] = core[0]
        #     torch.save(result.cpu().to(torch.float16),os.path.join(self.decode_result_dir, f'{t:05d}.pt'))
        # barrier()