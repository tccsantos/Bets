import gc
import sys
import torch
import argparse
import numpy as np

from argparse import RawTextHelpFormatter
from tqdm import tqdm
from PIL import Image
from pathlib import Path
from torchvision import models
from torch.utils.data import Dataset
from torch.utils.data import DataLoader
from transformers import CLIPProcessor, CLIPModel
from transformers import AutoImageProcessor, AutoModel


class Thumbnails(Dataset):

    def __init__(self, image_dir):
        self.files = [
            p for p in Path(image_dir).rglob("*")
            if p.suffix.lower() in {
                ".jpg", ".jpeg", ".png", ".webp"
            }
        ]

    def __len__(self):
        return len(self.files)

    def __getitem__(self, idx):
        path = self.files[idx]

        image = Image.open(path).convert("RGB")

        return image, str(path)


def clear():

    gc.collect()

    if torch.cuda.is_available():
        torch.cuda.empty_cache()

def read_options() -> dict[str, str|bool]:
    status = False

    parser = argparse.ArgumentParser(
        description="Basic Usage", formatter_class=RawTextHelpFormatter
    )

    parser.add_argument(
        "-dir", "--directory_name", help="Nome do diretório das imagens", required=True, default=""
    )

    argument = parser.parse_args()

    if argument.directory_name:
        status = True

    if not status:
        print("Maybe you want to use -h for help")
        status = False

    return {"success": status, "directory_name": argument.directory_name}

def get_data():
    data = read_options()
        
    if not data.get("success"):
        print("Erro no envio dos dados, checar argumentos!")
        print(data)
        sys.exit(0)

    dir = data.get("directory_name")
    if not isinstance(dir, str):
        print("Erro no envio dos dados, checar argumentos!")
        print(data)
        sys.exit(0)

    return dir

def resnet_settings(device: str):

    weights = models.ResNet50_Weights.DEFAULT

    resnet = models.resnet50(weights=weights)

    # ignorar aviso de erro
    resnet.fc = torch.nn.Identity()

    resnet = resnet.to(device)
    resnet.eval()

    resnet_transform = weights.transforms()

    # Teste
    # x = torch.randn(1, 3, 224, 224).to(device)

    # with torch.no_grad():
    #     embedding = resnet(x)

    # print(embedding.shape)

    return resnet, resnet_transform

def dino_settings(device: str):

    dino_processor = AutoImageProcessor.from_pretrained(
        "facebook/dinov2-base"
    )

    dino = AutoModel.from_pretrained(
        "facebook/dinov2-base"
    )

    dino = dino.to(device)
    dino.eval()

    return dino, dino_processor

def clip_settings(device):
    clip_processor = CLIPProcessor.from_pretrained(
        "openai/clip-vit-base-patch32"
    )

    clip = CLIPModel.from_pretrained(
        "openai/clip-vit-base-patch32"
    )

    clip = clip.to(device)
    clip.eval()

    return clip, clip_processor

def resnet_process(device, resnet, images):
    images = images.to(device)

    with torch.no_grad():
        embeddings = resnet(images)

    return embeddings.cpu().numpy()

def dino_process(device, dino, dino_processor, images):
    inputs = dino_processor(
        images=list(images),
        return_tensors="pt"
    )

    inputs = {
        k: v.to(device)
        for k, v in inputs.items()
    }

    with torch.no_grad():

        outputs = dino(**inputs)

        embeddings = outputs.last_hidden_state[:, 0]

    return embeddings.cpu().numpy()

def clip_process(device, clip, clip_processor, images):

    inputs = clip_processor(
        images=list(images),
        return_tensors="pt"
    )

    inputs = {
        k: v.to(device)
        for k, v in inputs.items()
    }

    with torch.no_grad():

        outputs = clip.vision_model(
            pixel_values=inputs["pixel_values"]
        )

        embeddings = outputs.pooler_output

        embeddings = clip.visual_projection(
            embeddings
        )

    return embeddings.cpu().numpy()

def pipeline(device, loader):

    paths = []
    resnet_inputs = None
    emb_resnet = None

    resnet_embeddings = []

    resnet, resnet_transform = resnet_settings(device)

    for images, batch_paths in tqdm(
        loader,
        total=len(loader),
        desc="ResNet"
    ):

        resnet_inputs = torch.stack([
            resnet_transform(img)
            for img in images
        ]).to(device)

        emb_resnet = resnet_process(
            device,
            resnet,
            resnet_inputs
        )

        resnet_embeddings.append(emb_resnet)

        paths.extend(batch_paths)

    resnet_embeddings = np.concatenate(
        resnet_embeddings,
        axis=0
    )

    np.save(
        "embeddings_resnet.npy",
        resnet_embeddings
    )

    np.save(
        "image_paths.npy",
        np.array(paths)
    )

    del resnet
    del resnet_inputs
    del emb_resnet
    del resnet_embeddings
    del paths

    clear()

    clip_embeddings = []
    emb_clip = None

    clip, clip_processor = clip_settings(device)

    for images, batch_paths in tqdm(
        loader,
        total=len(loader),
        desc="CLIP"
    ):

        emb_clip = clip_process(
            device,
            clip,
            clip_processor,
            images
        )

        clip_embeddings.append(emb_clip)

    clip_embeddings = np.concatenate(
        clip_embeddings,
        axis=0
    )

    np.save(
        "embeddings_clip.npy",
        clip_embeddings
    )

    # Libera CLIP
    del clip
    del emb_clip
    del clip_processor
    del clip_embeddings

    clear()

    dino_embeddings = []
    emb_dino = None

    dino, dino_processor = dino_settings(device)

    for images, batch_paths in tqdm(
        loader,
        total=len(loader),
        desc="DINOv2"
    ):

        emb_dino = dino_process(
            device,
            dino,
            dino_processor,
            images
        )

        dino_embeddings.append(emb_dino)

    dino_embeddings = np.concatenate(
        dino_embeddings,
        axis=0
    )

    np.save(
        "embeddings_dino.npy",
        dino_embeddings
    )

    del dino
    del emb_dino
    del dino_processor
    del dino_embeddings

    clear()

    print("\n" + "=" * 60)
    print("Pipeline concluído")
    print("=" * 60)

    print(f"Imagens:  {len(paths)}")
    print(f"ResNet:   {resnet_embeddings.shape}")
    print(f"CLIP:     {clip_embeddings.shape}")
    print(f"DINOv2:   {dino_embeddings.shape}")

def settings(images_path: str):

    dataset = Thumbnails(images_path)

    loader = DataLoader(
        dataset,
        batch_size=16,
        shuffle=False,
        collate_fn=lambda batch: (
            [x[0] for x in batch],
            [x[1] for x in batch]
        )
    )

    device = "cuda" if torch.cuda.is_available() else "cpu"

    return device, loader


def main():

    directory = get_data()

    device, loader = settings(directory)

    pipeline(device, loader)


if __name__ == "__main__":
    main()
