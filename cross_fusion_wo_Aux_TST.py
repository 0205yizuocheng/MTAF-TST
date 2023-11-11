import torch
import torch.nn as nn
from math import sqrt


class Cross_Wo_Aux_TST(nn.Module):

    def __init__(self, T=[23,23], input_c=[10,10], image_size=128, label_c=9, leve_dims=[32,64,128], dropout=0.5, dim_weight=64):
        super(Cross_Wo_Aux_TST, self).__init__()

        self.T=T
        self.input_c=input_c
        self.dims=leve_dims

        self.first_optic_conv_0=nn.Conv2d(input_c[0], int(self.dims[0]/2), kernel_size=3, padding=1)
        self.first_optic_bn_0 = nn.BatchNorm2d(int(self.dims[0]/2))
        self.first_optic_Relu_0 = nn.ReLU()
        self.first_optic_conv_1=nn.Conv2d(int(self.dims[0]/2), self.dims[0], kernel_size=3, padding=1)
        self.first_optic_bn_1 = nn.BatchNorm2d(self.dims[0])
        self.first_optic_Relu_1 = nn.ReLU()
        self.first_optic_globalavg = nn.AvgPool2d(kernel_size=image_size)
        self.second_optic_conv=nn.Conv2d(self.dims[0], self.dims[0], kernel_size=3, padding=1)
        self.second_optic_bn = nn.BatchNorm2d(self.dims[0])
        self.second_optic_Relu = nn.ReLU()
        self.second_optic_globalavg = nn.AvgPool2d(kernel_size=image_size)

        self.first_sar_conv_0=nn.Conv2d(input_c[1], int(self.dims[0]/2), kernel_size=3, padding=1)
        self.first_sar_bn_0 = nn.BatchNorm2d(int(self.dims[0]/2))
        self.first_sar_Relu_0 = nn.ReLU()
        self.first_sar_conv_1=nn.Conv2d(int(self.dims[0]/2), self.dims[0], kernel_size=3, padding=1)
        self.first_sar_bn_1 = nn.BatchNorm2d(self.dims[0])
        self.first_sar_Relu_1 = nn.ReLU()
        self.first_sar_globalavg = nn.AvgPool2d(kernel_size=image_size)
        self.second_sar_conv=nn.Conv2d(self.dims[0], self.dims[0], kernel_size=3, padding=1)
        self.second_sar_bn = nn.BatchNorm2d(self.dims[0])
        self.second_sar_Relu = nn.ReLU()
        self.second_sar_globalavg = nn.AvgPool2d(kernel_size=image_size)
        self.cross_Avg =nn.AvgPool3d(kernel_size=(T[0],1,1))

        self.Conconv=nn.Conv2d(self.dims[0], dim_weight, kernel_size=3, padding=1)
        self.Conbn = nn.BatchNorm2d(dim_weight)
        self.ConRelu = nn.ReLU()
        self.classconv = nn.Conv2d(dim_weight, label_c, kernel_size=3, padding=1)

        
            
    def forward(self, x1, x2):

        B, T1, E1, H, W=x1.shape
        x1 = x1.reshape(B*T1,E1,H,W)

        x1 = self.first_optic_conv_0(x1)
        x1 = self.first_optic_bn_0(x1)
        x1 = self.first_optic_Relu_0(x1)

        x1 = self.first_optic_conv_1(x1)
        x1 = self.first_optic_bn_1(x1)
        x1 = self.first_optic_Relu_1(x1)

        x1_avg = self.first_optic_globalavg(x1).squeeze().reshape(B,T1,self.dims[0])

        B, T2, E2, H, W=x2.shape

        x2 = x2.reshape(B*T2,E2,H,W)

        x2 = self.first_sar_conv_0(x2)
        x2 = self.first_sar_bn_0(x2)
        x2 = self.first_sar_Relu_0(x2)

        x2 = self.first_sar_conv_1(x2)
        x2 = self.first_sar_bn_1(x2)
        x2 = self.first_sar_Relu_1(x2)

        x2_avg = self.first_sar_globalavg(x2).squeeze().reshape(B,T2,self.dims[0])
        

        scores_1 = torch.bmm(x2_avg,x1_avg.permute(0,2,1))
        scale = 1./sqrt(E2)
        w_1 = torch.softmax(scale * scores_1, dim=-1)

        x2 = x2+torch.einsum("bpdhw,bsp->bsdhw", x1.reshape(B, T1, -1, H, W), w_1).reshape(B*T2, -1, H, W)#x2+

        x1 = self.second_optic_conv(x1)
        x1 = self.second_optic_bn(x1)
        x1 = self.second_optic_Relu(x1)

        x1_TST_avg = self.second_optic_globalavg(x1).squeeze().reshape(B,T1,self.dims[0])

        x2 = self.second_sar_conv(x2)
        x2 = self.second_sar_bn(x2)
        x2 = self.second_sar_Relu(x2)

        x2_TST_avg = self.second_sar_globalavg(x2).squeeze().reshape(B,T2,self.dims[0])

        scores_2 = torch.bmm(x1_TST_avg,x2_TST_avg.permute(0,2,1))
        scale = 1./sqrt(E1)
        w_2 = torch.softmax(scale * scores_2, dim=-1)

        x1 = x1+torch.einsum("bsdhw,bps->bpdhw", x2.reshape(B, T2, -1, H, W), w_2).reshape(B*T1, -1, H, W)#x1+

        x_up = x1.reshape(B, T1, -1, H, W)
        x_up = x_up.permute(0,2,1,3,4)
        
        x_up = self.cross_Avg(x_up)
        x = x_up.squeeze()
        
        x_con = self.Conconv(x)
        x_con = self.Conbn(x_con)
        x_con = self.ConRelu(x_con)
        
        output = self.classconv(x_con)

        
        return output
