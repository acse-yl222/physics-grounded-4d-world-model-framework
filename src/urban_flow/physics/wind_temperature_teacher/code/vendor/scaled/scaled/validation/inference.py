import torch
from scaled.model.unets.unet_3ds import UNet3DsModel
import pathlib
import pickle
import os
import math
import torch.distributed as dist
from tqdm import tqdm
import torch.nn.functional as F
import shutil

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

def save_tile(path: pathlib.Path, arr):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        pickle.dump(arr, f, protocol=pickle.HIGHEST_PROTOCOL)


def load_tile(path: pathlib.Path):
    with open(path, "rb") as f:
        return pickle.load(f)

def tile_path(root, kind, i, j, rank):
    # kind: "enc0", "encbg", "infer", "dec"
    return pathlib.Path(root) /f"{kind}_r{rank:03d}_{i:05d}_{j:05d}.pkl"


class LatentInferenceOnlyGeometryDDP:
    """
    在 latent 空间对 (latent_t, latent_geo) 做分片+halo 的并行推理，返回下一时刻 latent（CPU）。
    假设模型输出即为下一时刻 4 通道 latent（若为残差输出，可把赋值改为 self.latent_t += next_full）。
    """
    def __init__(self, inference_model: UNet3DsModel, 
                 latent_geo,
                 save_dir,
                 device: torch.device,
                 rank: int, 
                 world_size: int, 
                 halo_lat_infer=2):
        self.save_dir = save_dir
        self.tiles_path = os.path.join(self.save_dir,'inference_tem_tiles')
        self.result_path = os.path.join(self.save_dir,'inference_latent_result')
        self.model = inference_model.to(device).eval()
        self.device = device
        self.rank = rank
        self.world_size = world_size
        self.latent_geo = latent_geo
        self.halo_lat = halo_lat_infer
        self.B, self.C_lat, self.D_lat, self.H_lat, self.W_lat = self.latent_geo.shape

    @torch.no_grad()
    def step_once(self, latent_t,tile_lat=64):
        ## inference latent
        B, _, D_lat, H_lat, W_lat = self.latent_geo.shape
        halo_lat = self.halo_lat

        # 拼接通道：8 = 4(latent_t) + 4(geo)（CPU）
        stacked = torch.cat([latent_t, self.latent_geo], dim=1)

        n_rows = math.ceil(H_lat / tile_lat)
        n_cols = math.ceil(W_lat / tile_lat)

        for i, j in tile_iterator(n_rows, n_cols, self.rank, self.world_size):
            print(f'rank {self.rank} processing {i*16+j} latent')
            y0 = i * tile_lat
            x0 = j * tile_lat
            y1 = y0 + tile_lat + 2 * halo_lat
            x1 = x0 + tile_lat + 2 * halo_lat

            # ---- 以原始 stacked 为基准，先算“想要”的窗口，再裁、再局部 pad ----
            # 想要的窗口（在未pad坐标系中）：包含 tile 本体 + 两侧 halo
            want_y0 = y0 - halo_lat
            want_y1 = y1 - halo_lat
            want_x0 = x0 - halo_lat
            want_x1 = x1 - halo_lat

            # 实际可从原图取到的范围（裁剪到 [0, H_lat) × [0, W_lat) 里）
            src_y0 = max(0, want_y0)
            src_y1 = min(H_lat, want_y1)
            src_x0 = max(0, want_x0)
            src_x1 = min(W_lat, want_x1)

            # 需要补的边界大小（在 H/W 两维上）；注意 F.pad 的顺序是 (left, right, top, bottom, front, back)
            pad_top    = max(0, 0       - want_y0)         # 想要的上边越界了多少
            pad_bottom = max(0, want_y1 - H_lat)           # 想要的下边越界了多少
            pad_left   = max(0, 0       - want_x0)
            pad_right  = max(0, want_x1 - W_lat)

            # 从原图裁出最小子块（CPU）
            sub_cpu = stacked[:, :, :, src_y0:src_y1, src_x0:src_x1].contiguous()
            
            h_sub = sub_cpu.shape[-2]
            w_sub = sub_cpu.shape[-1]
            if ((pad_top    >= h_sub) or (pad_bottom >= h_sub) or
                (pad_left   >= w_sub) or (pad_right  >= w_sub)):
                pad_mode = "replicate"
            else:
                pad_mode = "replicate"

            # 只在 H/W 维上做局部 pad（D 维不动）
            if pad_top or pad_bottom or pad_left or pad_right:
                sub_cpu = F.pad(
                    sub_cpu,
                    (pad_left, pad_right, pad_top, pad_bottom, 0, 0),  # (W_left, W_right, H_top, H_bottom, D_front, D_back)
                    mode=pad_mode,
                )

            # 现在 sub_cpu 的空间尺寸应为：(tile_lat + 2*halo_lat, tile_lat + 2*halo_lat)
            # 传到 GPU
            sub = sub_cpu.pin_memory().to(self.device, non_blocking=True)

            # sub = inp_pad[:, :, :, y0:y1, x0:x1].pin_memory().to(self.device, non_blocking=True)

            with torch.amp.autocast(device_type="cuda", dtype=torch.float32):
                pred = self.model(sub).sample  # 期望 [B,4,D, tile_lat+2h, tile_lat+2h]

            # 如果模型输出不是等尺寸，做插值对齐
            if pred.shape[-2] != (tile_lat + 2 * halo_lat) or pred.shape[-1] != (tile_lat + 2 * halo_lat):
                pred = F.interpolate(pred, size=(tile_lat + 2 * halo_lat, tile_lat + 2 * halo_lat),
                                     mode="trilinear", align_corners=False)

            # 取核心 tile_lat×tile_lat（GPU->CPU）
            core = pred[:, :, :, halo_lat:halo_lat + tile_lat, halo_lat:halo_lat + tile_lat] \
                       .to("cpu", non_blocking=False)

            Y0 = i * tile_lat
            X0 = j * tile_lat
            Y1 = min(Y0 + tile_lat, H_lat)
            X1 = min(X0 + tile_lat, W_lat)
            core = core[:, :, :, :Y1 - Y0, :X1 - X0]
            save_tile(tile_path(self.tiles_path, "infer", i, j, self.rank), core)
        barrier()
        if is_main(self.rank):
            print('starting to combine the latent.....')
            next_full = torch.zeros_like(latent_t)  # CPU
            for i in range(n_rows):
                for j in range(n_cols):
                    found = False
                    for r in range(self.world_size):
                        p = tile_path(self.tiles_path, "infer", i, j, r)
                        if p.exists():
                            core = load_tile(p)
                            found = True
                            break
                    if not found:
                        raise RuntimeError(f"Missing infer tile ({i},{j})")
                    Y0 = i * tile_lat
                    X0 = j * tile_lat
                    Y1 = min(Y0 + tile_lat, H_lat)
                    X1 = min(X0 + tile_lat, W_lat)
                    next_full[:, :, :, Y0:Y1, X0:X1] = core
        if is_main(self.rank):
            tmp = next_full.to(self.device, non_blocking=True)   # 先上 GPU：NCCL 只支持 CUDA 张量广播
        else:
            tmp = torch.empty_like(latent_t, device=self.device)
        dist.broadcast(tmp, src=0)
        latent_t = tmp.to("cpu", non_blocking=True)
        barrier()
        return latent_t

    @torch.no_grad()
    def run(self, initial_t,steps=100,tile_lat=512):
        os.makedirs(self.result_path, exist_ok=True)
        latent_t = initial_t
        barrier()
        if is_main(self.rank):
            torch.save(latent_t.clone().to(torch.float16), os.path.join(self.result_path, f"{0:05d}.pt"))
        for t in tqdm(range(1, steps + 1)):
            if is_main(self.rank):
                shutil.rmtree(self.tiles_path, ignore_errors=True)
            barrier()
            os.makedirs(self.tiles_path, exist_ok=True)
            barrier()
            latent_t = self.step_once(latent_t=latent_t,tile_lat=tile_lat)
            if is_main(self.rank):
                torch.save(latent_t.clone().to(torch.float16), os.path.join(self.result_path, f"{t:05d}.pt"))