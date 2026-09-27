import torch
import torch.nn as nn

from diffusers.models.modeling_utils import ModelMixin


class CAE(ModelMixin):
    def __init__(self, channels = 7):
        super(CAE, self).__init__()


        self.encoder = torch.nn.Sequential(
            torch.nn.Conv3d(channels, 16, kernel_size=3, stride=1, padding=1),
            torch.nn.LeakyReLU(True),
            torch.nn.BatchNorm3d(16),

            torch.nn.Conv3d(16, 32, kernel_size=3, stride=1, padding=1),
            torch.nn.LeakyReLU(True),
            torch.nn.BatchNorm3d(32),

            torch.nn.MaxPool3d(2, stride=2),

            torch.nn.Conv3d(32, 64, kernel_size=3, stride=1, padding=1),
            torch.nn.LeakyReLU(True),
            torch.nn.BatchNorm3d(64),

            torch.nn.Conv3d(64, 128, kernel_size=3, stride=1, padding=1),
            torch.nn.LeakyReLU(True),
            torch.nn.BatchNorm3d(128),

            torch.nn.Conv3d(128, channels-1, kernel_size=3, stride=1, padding=1),
            torch.nn.LeakyReLU(True),
            torch.nn.BatchNorm3d(channels-1),


            torch.nn.MaxPool3d(2,stride=2),

            torch.nn.Flatten(),
            torch.nn.Linear((channels-1)*4*4*4, 512),
            torch.nn.LeakyReLU(True), 
            torch.nn.Sigmoid(), 
       
        )

        self.decoder = torch.nn.Sequential(
           
            torch.nn.Linear(512, (channels-1)*4*4*4),
            torch.nn.LeakyReLU(True),
            torch.nn.Unflatten(1, (channels-1, 4, 4, 4)),
            
            torch.nn.Upsample(scale_factor=2, mode='nearest'),
            
            torch.nn.ConvTranspose3d(channels-1, 128, kernel_size=3, stride=1, padding=1),
            torch.nn.LeakyReLU(True),
            torch.nn.BatchNorm3d(128),

            torch.nn.ConvTranspose3d(128, 64, kernel_size=3, stride=1, padding=1),
            torch.nn.LeakyReLU(True),
            torch.nn.BatchNorm3d(64),

            torch.nn.ConvTranspose3d(64, 32, kernel_size=3, stride=1, padding=1),
            torch.nn.LeakyReLU(True),
            torch.nn.BatchNorm3d(32),

            torch.nn.Upsample(scale_factor=2, mode='nearest'),


            torch.nn.ConvTranspose3d(32, 16, kernel_size=3, stride=1, padding=1),
            torch.nn.LeakyReLU(True),
            torch.nn.BatchNorm3d(16),
            
            torch.nn.ConvTranspose3d(16, channels-1, kernel_size=3, stride=1, padding=1),
            torch.nn.Sigmoid()
        )

    def forward(self, x):
   

        # Encode and decode
        x = self.encoder(x)
        x = self.decoder(x)


        return x

class MaskCAE(ModelMixin):
    def __init__(self, channels=1):
        super(MaskCAE, self).__init__()

        self.encoder = nn.Sequential(
            nn.Flatten(),
            
            nn.Linear(channels*16*16*16, 512),
            nn.ReLU(True),
            # nn.Dropout(0.2),

            # nn.Linear(4096,4096),
            # nn.ReLU(True),
            # nn.Dropout(0.2),

            # nn.Linear(4096, 1024),
            # nn.ReLU(True),
            # nn.Dropout(0.2),

            # nn.Linear(1024, 512),
            # nn.ReLU(True),

            nn.Sigmoid()
            
            

        
        )

        self.decoder = nn.Sequential(

            # nn.Unflatten(1, (64,2,2,2)),
       
            # nn.Linear(512, 1024),
            # nn.ReLU(True),
            # nn.Dropout(0.2),

            # nn.Linear(1024, 4096),
            # nn.ReLU(True),
            # nn.Dropout(0.2),

            # # nn.Linear(4096, 4096),
            # # nn.ReLU(True),
            # # nn.Dropout(0.2),

            nn.Linear(512, 16*16*16),
            nn.Unflatten(1, (1,16,16,16)),
            nn.Sigmoid()
        )

    def forward(self, x):
        # Encode
        z = self.encoder(x)
        # Decode
        x = self.decoder(z)
    
        return x, z
    



# # visualisation function
# temp = torch.tensor(encoded_particles[idx],dtype=torch.float)

# a = tools.revert_mask(tools.threshold(model_mask.decoder(temp).detach().numpy()))[0]
# plot = np.argwhere(a==1)
# z,y,x = plot[:,0], plot[:,1], plot[:,2]
# fig = plt.figure(figsize=(10,10))
# ax = fig.add_subplot(111, projection='3d')
# ax.scatter(x, y, z, zdir='z', s = 8)
# ax.set_box_aspect([1,1,3])
# ax.view_init( azim=60)

# plt.show()