import timm, torch
from torch import nn 
from ultralytics import YOLO
class Model5Cond(nn.Module):
    def __init__(self, cond_dim):
        super().__init__()

        self.img_encoder = timm.create_model(
            "efficientnet_b0",
            pretrained=False,
            num_classes=0
        )
        img_dim = self.img_encoder.num_features

        self.lstm = nn.LSTM(
            input_size=48,
            hidden_size=256,
            batch_first=True,
            bidirectional=True
        )

        self.cond_fc = nn.Sequential(
            nn.Linear(cond_dim, 32),
            nn.ReLU()
        )

        self.head = nn.Sequential(
            nn.Linear(img_dim + 512 + 32, 256),
            nn.ReLU(),
            nn.Linear(256, cond_dim),
            nn.Sigmoid()
        )

    def forward(self, img, seq, cond):
        img_f = self.img_encoder(img)
        lstm_out, _ = self.lstm(seq)
        seq_f = lstm_out[:, -1]
        cond_f = self.cond_fc(cond)
        x = torch.cat([img_f, seq_f, cond_f], dim=1)
        return self.head(x)

