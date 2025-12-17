import torch, cv2
import numpy as np 
from PIL import Image
from ultralytics import YOLO
from torchvision import transforms

from utils.network import Model5Cond


detector = YOLO("./utils/weights/yolov8n-pose.pt")
net = Model5Cond(5)
weight = torch.load(
    "./utils/weights/model_kneepushup.pth",
    map_location=torch.device("cpu"))
net.load_state_dict(weight)
net.eval()

data = np.load(r"c:\Users\human\Documents\카카오톡 받은 파일\kneepushup\kneepushup_npzs\train\니푸쉬업\D33-1-593_seq_0.npz", allow_pickle=True)
data["seq"]

seq = torch.tensor(data["seq"], dtype=torch.float32)
conds = data["type_info"].item()["conditions"]
label = torch.tensor([1.0 if c["value"] else 0.0 for c in conds], dtype=torch.float32)

# RGB 순 
pil_img = Image.open(r"c:\Users\human\Documents\카카오톡 받은 파일\kneepushup\kneepushup_images\train\니푸쉬업\593-1-3-28-Z1_A-0000001.jpg")
img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

preprocess = transforms.Compose([
    transforms.ToPILImage(),
    transforms.Resize((256,256)),
    transforms.ToTensor()
])


input_tensor = preprocess(img)
input_tensor = torch.unsqueeze(input_tensor,0)
with torch.no_grad():
    pred = net(input_tensor)



video_path = r"c:\Users\human\Documents\카카오톡 받은 파일\kneepushup\video_kneepushup.mp4"

def getAllFrames(video_path):
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps is None or fps <= 1:
        fps = 30  # 🔥 필수 fallback
    frames = []
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        frames.append(frame)
    return frames


frames = getAllFrames(video_path)
frames = np.array(frames)
len(frames) # 578
res = [detector(frame, verbose = False)[0] for frame in frames]
xy_data = [i.keypoints.xy.detach().cpu().numpy() for i in res]
[i.shape for i in xy_data]
np.array(xy_data)

