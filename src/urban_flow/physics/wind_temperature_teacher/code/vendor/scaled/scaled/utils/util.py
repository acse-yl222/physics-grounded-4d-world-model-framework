import importlib
import os
import os.path as osp
import shutil
import sys
import numpy as np
import matplotlib.pyplot as plt
import torch

def seed_everything(seed):
    import random

    import numpy as np

    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    np.random.seed(seed % (2**32))
    random.seed(seed)

def import_filename(filename):
    spec = importlib.util.spec_from_file_location("mymodule", filename)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module

def delete_additional_ckpt(base_path, num_keep):
    dirs = []
    for d in os.listdir(base_path):
        if d.startswith("checkpoint-"):
            dirs.append(d)
    num_tot = len(dirs)
    if num_tot <= num_keep:
        return
    # ensure ckpt is sorted and delete the ealier!
    del_dirs = sorted(dirs, key=lambda x: int(x.split("-")[-1]))[: num_tot - num_keep]
    for d in del_dirs:
        path_to_dir = osp.join(base_path, d)
        if osp.exists(path_to_dir):
            shutil.rmtree(path_to_dir)

class tools:
    def __init__(self):
        pass

    @staticmethod
    def visualise(data, vel = [0],azim = 60,aspect = [1,1,1] ,mask = True):

        #apply mask
        if mask is True:
            mask = data[-1].astype(bool)
        else:
            mask = np.ones(data[0].shape).astype(bool)
        data = data[:,mask]


        fig = plt.figure(figsize=(8, 8))
        ax = fig.add_subplot(111, projection="3d")
        if len(vel)>1:
            sc = ax.scatter(data[0],data[1],data[2], c=vel, cmap="coolwarm", edgecolors='gray', s=8, vmin=0, vmax=1.7)
        else:
            vel = (data[3]**2+data[4]**2+data[5]**2)**0.5
            sc = ax.scatter(data[0],data[1],data[2],c = vel, cmap="coolwarm", edgecolors='gray', s=8, vmin=0, vmax=1.7)
        # plt.colorbar(sc, shrink=0.35)
        cbar = plt.colorbar(sc, orientation='vertical', shrink=0.75)
        cbar.set_label('Particle speed (m/s)',fontsize=15)
        # sc = ax.scatter(xp[::1],yp[::1],zp[::1], facecolors='white',edgecolors='gray',s=S_graph)
        ax = plt.gca()
        ax.set_xlim([0, 1])
        ax.set_ylim([0, 1])
        ax.set_zlim([0, 1])
        ax.view_init(elev=30, azim=azim)

        # ax.set_xlabel('x')
        # ax.set_ylabel('y')
        # ax.set_zlabel('z')
        ax.set_box_aspect(aspect)
        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_zticks([])
        # ax.set_axis_off()


    @staticmethod
    def revert_subdomain(split_data, midpoints, mins, maxs, mask = None):
        channels = split_data.shape[1]
        #Take mask from data if not given
        if mask is None:
            mask = np.ones_like(split_data[:,0])



        denormalized_data = np.zeros(split_data.shape)
        for i in range(split_data.shape[0]):
        #create scaler in the same shape
            subdomain = np.zeros(split_data[i].shape)
            subdomain[:3] = split_data[i,:3]*(maxs[i]-mins[i]) + mins[i]
            subdomain[:3] += midpoints[i]
            subdomain[3:] = split_data[i,3:]
            denormalized_data[i] = subdomain

        # Initialize the reverted data array with the original shape
        reverted_data = np.zeros(( channels, 256, 64, 64))

        idx = 0
        for z in range(4):
            for y in range(4):
                for x in range(16):
                    reshaped_mask =np.tile((mask == 1).reshape(256,1,16,16,16),(1,6,1,1,1))
                    reverted_data[ :6, x*16:(x+1)*16, y*16:(y+1)*16, z*16:(z+1)*16] = denormalized_data[idx][:6]*reshaped_mask[idx]
                    reverted_data[ 6:, x*16:(x+1)*16, y*16:(y+1)*16, z*16:(z+1)*16] = denormalized_data[idx][6:]


                    idx += 1


        return reverted_data

    @staticmethod
    def apply_model_whole_domain(data, model, type = 'CAE'
                                ):
        # Get the shape of the input data
        # Calculate the number of splits needed

        # Initialize an empty array to store the reverted data
        channels = data.shape[1]
        reverted = np.zeros_like(data)[:,:channels-1]

        # Process each split
        for i in range(256):

            # Extract the current split
            # Apply the model to the current split
            if type == 'CAE':
                split_output = model(torch.tensor(data[i].reshape(1, channels, 16, 16, 16), dtype=torch.float32)).cpu().detach().numpy()
            elif type == 'VAE':

                split_output, _, _  = model(torch.tensor(data[i].reshape(1, channels, 16, 16, 16), dtype=torch.float32).to(model.device))
                split_output = split_output.cpu().detach().numpy()
            # Place the split output back into the reverted array
            reverted[ i,:,:, :] = split_output[0]  # Remove batch dimension

        return reverted

    @staticmethod
    def plot_losses(train_loss,val_loss = 0, name = 'plot', dir = 'plots/'):
        plt.plot(train_loss, label='Train Loss')
        if val_loss !=0:
            plt.plot(val_loss, label='Validation Loss')
        plt.xlabel('Epochs')
        plt.ylabel('Loss')
        plt.legend()
        plt.savefig(dir+ name + '.png')
        plt.close()

    @staticmethod
    def revert_mask(temp):
        reverted_data = np.zeros((1,256,64,64))
        idx = 0
        for z in range(4):
            for y in range(4):
                for x in range(16):
                    reshaped_mask =np.tile((temp == 1).reshape(256,1,16,16,16),(1,1,1,1,1))
                    reverted_data[ 0, x*16:(x+1)*16, y*16:(y+1)*16, z*16:(z+1)*16] =reshaped_mask[idx]


                    idx += 1

        return reverted_data
    def revert_data(data, mask):
            reverted_data = np.zeros((1,256,64,64))
            idx = 0
            for z in range(4):
                for y in range(4):
                    for x in range(16):
                            reshaped_mask =np.tile((mask == 1).reshape(256,1,16,16,16),(1,1,1,1,1))
                            reverted_data[ 0, x*16:(x+1)*16, y*16:(y+1)*16, z*16:(z+1)*16] =reshaped_mask[idx]*data[idx]

                            idx += 1

            return reverted_data
    def threshold(probs, n= 58621):
        """
        Retain the top n highest probabilities in the array, setting the rest to 0.

        Parameters:
        probs (numpy.ndarray): Array of predicted probabilities.
        n (int): Number of top probabilities to retain.

        Returns:
        numpy.ndarray: Array with top n probabilities retained, others set to 0.
        """
        s1, s2, s3, s4, s5 = probs.shape
        if n >= np.prod(probs.shape):
            return probs  # If n is greater than or equal to the length of probs, return original array

        # Find the indices of the top n probabilities
        top_n_indices = np.argpartition(probs.flatten(), -n)[-n:]

        # Create an array of zeros
        top_n_probs = np.zeros_like(probs.flatten())
        # Set the top n probabilities
        top_n_probs[top_n_indices] = 1

        return top_n_probs.reshape(s1,s2,s3,s4,s5)


    def create_gaussian_kernel_3d(kernel_size=3, sigma=1.0):
        """
        Creates a 3D Gaussian kernel.

        Args:
            kernel_size (int): The size of the kernel (must be an odd number).
            sigma (float): The standard deviation of the Gaussian distribution.

        Returns:
            torch.Tensor: 3D Gaussian kernel.
        """
        # Ensure the kernel size is odd
        if kernel_size % 2 == 0:
            raise ValueError("Kernel size must be an odd number.")

        # Create a coordinate grid centered at zero
        ax = torch.arange(-kernel_size // 2 + 1, kernel_size // 2 + 1, dtype=torch.float32)
        xx, yy, zz = torch.meshgrid(ax, ax, ax)
        grid = torch.stack([xx, yy, zz], dim=-1)

        # Compute the Gaussian kernel
        kernel = torch.exp(-torch.sum(grid**2, dim=-1) / (2 * sigma**2))
        kernel = kernel / torch.sum(kernel)

        return kernel.unsqueeze(0).unsqueeze(0)


    def revert_data(data):
            reverted_data = np.zeros((data.shape[1],256,64,64))
            idx = 0
            for z in range(4):
                for y in range(4):
                    for x in range(16):
                            reverted_data[ :, x*16:(x+1)*16, y*16:(y+1)*16, z*16:(z+1)*16] =data[idx]

                            idx += 1

            return reverted_data
    def f1(y_true, y_pred, threshold=0.5): #higher is better

        # Convert probabilities to binary predictions
        y_pred = (y_pred > threshold).astype(np.float32)

        # Calculate True Positives (TP), False Positives (FP), and False Negatives (FN)
        tp = np.sum(y_true * y_pred)
        fp = np.sum((1 - y_true) * y_pred)
        fn = np.sum(y_true * (1 - y_pred))
        tn = np.sum((1 - y_true) * (1 - y_pred))
        print("tp: ", tp, "fp: ", fp, "fn: ", fn, "tn: ", tn)

        # Calculate Precision and Recall
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0

        # Calculate F1-score
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

        return f1

class tools:
    def __init__(self):
        pass

    @staticmethod
    def visualise(data, vel=[0], azim=60, aspect=[1, 1, 1], mask=True):

        # apply mask
        if mask is True:
            mask = data[-1].astype(bool)
        else:
            mask = np.ones(data[0].shape).astype(bool)
        data = data[:, mask]

        fig = plt.figure(figsize=(8, 8))
        ax = fig.add_subplot(111, projection="3d")
        if len(vel) > 1:
            sc = ax.scatter(data[0], data[1], data[2], c=vel, cmap="coolwarm", edgecolors='gray', s=8, vmin=0, vmax=1.7)
        else:
            vel = (data[3] ** 2 + data[4] ** 2 + data[5] ** 2) ** 0.5
            sc = ax.scatter(data[0], data[1], data[2], c=vel, cmap="coolwarm", edgecolors='gray', s=8, vmin=0, vmax=1.7)
        # plt.colorbar(sc, shrink=0.35)
        cbar = plt.colorbar(sc, orientation='vertical', shrink=0.75)
        cbar.set_label('Particle speed (m/s)', fontsize=15)
        # sc = ax.scatter(xp[::1],yp[::1],zp[::1], facecolors='white',edgecolors='gray',s=S_graph)
        ax = plt.gca()
        ax.set_xlim([0, 1])
        ax.set_ylim([0, 1])
        ax.set_zlim([0, 1])
        ax.view_init(elev=30, azim=azim)

        # ax.set_xlabel('x')
        # ax.set_ylabel('y')
        # ax.set_zlabel('z')
        ax.set_box_aspect(aspect)
        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_zticks([])
        # ax.set_axis_off()

    @staticmethod
    def revert_subdomain(split_data, midpoints, mins, maxs, mask=None):
        channels = split_data.shape[1]
        # Take mask from data if not given
        if mask is None:
            mask = np.ones_like(split_data[:, 0])

        denormalized_data = np.zeros(split_data.shape)
        for i in range(split_data.shape[0]):
            # create scaler in the same shape
            subdomain = np.zeros(split_data[i].shape)
            subdomain[:3] = split_data[i, :3] * (maxs[i] - mins[i]) + mins[i]
            subdomain[:3] += midpoints[i]
            subdomain[3:] = split_data[i, 3:]
            denormalized_data[i] = subdomain

        # Initialize the reverted data array with the original shape
        reverted_data = np.zeros((channels, 256, 64, 64))

        idx = 0
        for z in range(4):
            for y in range(4):
                for x in range(16):
                    reshaped_mask = np.tile((mask == 1).reshape(256, 1, 16, 16, 16), (1, 6, 1, 1, 1))
                    reverted_data[:6, x * 16:(x + 1) * 16, y * 16:(y + 1) * 16, z * 16:(z + 1) * 16] = \
                    denormalized_data[idx][:6] * reshaped_mask[idx]
                    reverted_data[6:, x * 16:(x + 1) * 16, y * 16:(y + 1) * 16, z * 16:(z + 1) * 16] = \
                    denormalized_data[idx][6:]

                    idx += 1

        return reverted_data

    @staticmethod
    def apply_model_whole_domain(data, model, type='CAE'
                                 ):
        # Get the shape of the input data
        # Calculate the number of splits needed

        # Initialize an empty array to store the reverted data
        channels = data.shape[1]
        reverted = np.zeros_like(data)[:, :channels - 1]

        # Process each split
        for i in range(256):

            # Extract the current split
            # Apply the model to the current split
            if type == 'CAE':
                split_output = model(
                    torch.tensor(data[i].reshape(1, channels, 16, 16, 16), dtype=torch.float32)).cpu().detach().numpy()
            elif type == 'VAE':
                split_output, _, _ = model(
                    torch.tensor(data[i].reshape(1, channels, 16, 16, 16), dtype=torch.float32).to(model.device))
                split_output = split_output.cpu().detach().numpy()
            # Place the split output back into the reverted array
            reverted[i, :, :, :] = split_output[0]  # Remove batch dimension

        return reverted

    @staticmethod
    def plot_losses(train_loss, val_loss=0, name='plot', dir='plots/'):
        plt.plot(train_loss, label='Train Loss')
        if val_loss != 0:
            plt.plot(val_loss, label='Validation Loss')
        plt.xlabel('Epochs')
        plt.ylabel('Loss')
        plt.legend()
        plt.savefig(dir + name + '.png')
        plt.close()

    @staticmethod
    def revert_mask(temp):
        reverted_data = np.zeros((1, 256, 64, 64))
        idx = 0
        for z in range(4):
            for y in range(4):
                for x in range(16):
                    reshaped_mask = np.tile((temp == 1).reshape(256, 1, 16, 16, 16), (1, 1, 1, 1, 1))
                    reverted_data[0, x * 16:(x + 1) * 16, y * 16:(y + 1) * 16, z * 16:(z + 1) * 16] = reshaped_mask[idx]

                    idx += 1

        return reverted_data

    def revert_data(data, mask):
        reverted_data = np.zeros((1, 256, 64, 64))
        idx = 0
        for z in range(4):
            for y in range(4):
                for x in range(16):
                    reshaped_mask = np.tile((mask == 1).reshape(256, 1, 16, 16, 16), (1, 1, 1, 1, 1))
                    reverted_data[0, x * 16:(x + 1) * 16, y * 16:(y + 1) * 16, z * 16:(z + 1) * 16] = reshaped_mask[
                                                                                                          idx] * data[
                                                                                                          idx]

                    idx += 1

        return reverted_data

    def threshold(probs, n=58621):
        """
        Retain the top n highest probabilities in the array, setting the rest to 0.

        Parameters:
        probs (numpy.ndarray): Array of predicted probabilities.
        n (int): Number of top probabilities to retain.

        Returns:
        numpy.ndarray: Array with top n probabilities retained, others set to 0.
        """
        s1, s2, s3, s4, s5 = probs.shape
        if n >= np.prod(probs.shape):
            return probs  # If n is greater than or equal to the length of probs, return original array

        # Find the indices of the top n probabilities
        top_n_indices = np.argpartition(probs.flatten(), -n)[-n:]

        # Create an array of zeros
        top_n_probs = np.zeros_like(probs.flatten())
        # Set the top n probabilities
        top_n_probs[top_n_indices] = 1

        return top_n_probs.reshape(s1, s2, s3, s4, s5)

    def create_gaussian_kernel_3d(kernel_size=3, sigma=1.0):
        """
        Creates a 3D Gaussian kernel.

        Args:
            kernel_size (int): The size of the kernel (must be an odd number).
            sigma (float): The standard deviation of the Gaussian distribution.

        Returns:
            torch.Tensor: 3D Gaussian kernel.
        """
        # Ensure the kernel size is odd
        if kernel_size % 2 == 0:
            raise ValueError("Kernel size must be an odd number.")

        # Create a coordinate grid centered at zero
        ax = torch.arange(-kernel_size // 2 + 1, kernel_size // 2 + 1, dtype=torch.float32)
        xx, yy, zz = torch.meshgrid(ax, ax, ax)
        grid = torch.stack([xx, yy, zz], dim=-1)

        # Compute the Gaussian kernel
        kernel = torch.exp(-torch.sum(grid ** 2, dim=-1) / (2 * sigma ** 2))
        kernel = kernel / torch.sum(kernel)

        return kernel.unsqueeze(0).unsqueeze(0)

    def revert_data(data):
        reverted_data = np.zeros((data.shape[1], 256, 64, 64))
        idx = 0
        for z in range(4):
            for y in range(4):
                for x in range(16):
                    reverted_data[:, x * 16:(x + 1) * 16, y * 16:(y + 1) * 16, z * 16:(z + 1) * 16] = data[idx]

                    idx += 1

        return reverted_data

    def f1(y_true, y_pred, threshold=0.5):  # higher is better

        # Convert probabilities to binary predictions
        y_pred = (y_pred > threshold).astype(np.float32)

        # Calculate True Positives (TP), False Positives (FP), and False Negatives (FN)
        tp = np.sum(y_true * y_pred)
        fp = np.sum((1 - y_true) * y_pred)
        fn = np.sum(y_true * (1 - y_pred))
        tn = np.sum((1 - y_true) * (1 - y_pred))
        print("tp: ", tp, "fp: ", fp, "fn: ", fn, "tn: ", tn)

        # Calculate Precision and Recall
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0

        # Calculate F1-score
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

        return f1


def patch(data):
        data_result = []
        index_list = []
        for d_index in range(0, 256//32):
            for h_index in range(0, 64//32):
                for w_index in range(0, 64//32):
                    data_result.append(data[:,d_index*32:d_index*32+32,h_index*32:h_index*32+32,w_index*32:w_index*32+32])
                    index_list.append([(d_index*32,d_index*32+32),(h_index*32,h_index*32+32),(w_index*32,w_index*32+32)])
        for d_index in range(0,256//32-1):
            for h_index in range(0, 64//32-1):
                for w_index in range(0, 64//32-1):
                    data_result.append(data[:,d_index*32+16:d_index*32+32+16,h_index*32+16:h_index*32+32+16,w_index*32+16:w_index*32+32+16])
                    index_list.append([(d_index*32+16,d_index*32+32+16),(h_index*32+16,h_index*32+32+16),(w_index*32+16,w_index*32+32+16)])
        return torch.stack(data_result),index_list
    
    
def patch_4Nx(data):
        data_result = []
        index_list = []
        for d_index in range(0, 10):
            for h_index in range(0, 2):
                for w_index in range(0, 2):
                    data_result.append(data[:,d_index*24:d_index*24+32,h_index*24:h_index*24+32,w_index*24:w_index*24+32])
                    index_list.append([(d_index*24,d_index*24+32),(h_index*24,h_index*24+32),(w_index*24,w_index*24+32)])
        return torch.stack(data_result),index_list
    
def patch_4Nx_flow(data):
        data_result = []
        index_list = []
        for d_index in range(1):
            for h_index in range(0, 10):
                for w_index in range(0, 10):
                    data_result.append(data[:,d_index*48:d_index*48+64,h_index*48:h_index*48+64,w_index*48:w_index*48+64])
                    index_list.append([(d_index*48,d_index*48+64),(h_index*48,h_index*48+64),(w_index*48,w_index*48+64)])
        return torch.stack(data_result),index_list

def patch_4Nx_flow_past_building(data,d,h,w,width_ub,width_boundary):
        _,d,h,w = data.shape
        data_result = []
        index_list = []
        skip_d = d-2*width_ub
        skip_h = h-2*width_boundary
        skip_w = w-2*width_boundary
        for d_index in range(1):
            for h_index in range(0, (h-2*width_boundary)//skip_h):
                for w_index in range(0, (w-2*width_boundary)//skip_w):
                    data_result.append(data[:,d_index*skip_d:d_index*skip_d+d,
                                            h_index*skip_h:h_index*skip_h+h,
                                            w_index*skip_w:w_index*skip_w+w])
                    index_list.append([(d_index*skip_d,d_index*skip_d+d),
                                       (h_index*skip_h,h_index*skip_h+h),
                                       (w_index*skip_w,w_index*skip_w+w)])
        return torch.stack(data_result),index_list
    

def patch_4Nx_unconpress_flow(data):
    data_result = []
    index_list = []
    for d_index in range(1):
        for h_index in range(0,20):
            for w_index in range(0, 20):
                data_result.append(data[:,d_index*24:d_index*24+32,h_index*24:h_index*24+32,w_index*24:w_index*24+32])
                index_list.append([(d_index*24,d_index*24+32),(h_index*24,h_index*24+32),(w_index*24,w_index*24+32)])
    return torch.stack(data_result),index_list