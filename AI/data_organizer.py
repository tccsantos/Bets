from Collector.Apoio.my_mongo import get_all_collections_name_mongo, get_collection_mongo

import os
import glob
import numpy as np
import pandas as pd
import umap.umap_ as umap
import matplotlib.pyplot as plt


def convert_to_df(embeddings_dir: str, parquets_dir: str):
    if not os.path.exists(embeddings_dir + "embeddings_clip.npy"):
        raise ValueError
    embeddings_clip = np.load(embeddings_dir + "embeddings_clip.npy")

    if not os.path.exists(embeddings_dir + "embeddings_resnet.npy"):
        raise ValueError
    embeddings_resnet = np.load(embeddings_dir + "embeddings_resnet.npy")

    if not os.path.exists(embeddings_dir + "embeddings_yolo.npy"):
        raise ValueError
    embeddings_yolo = np.load(embeddings_dir + "embeddings_yolo.npy")

    if not os.path.exists(embeddings_dir + "image_paths.npy"):
        raise ValueError
    paths = np.load(embeddings_dir + "image_paths.npy")

    assert len(embeddings_clip) == len(paths)
    assert len(embeddings_resnet) == len(paths)
    assert len(embeddings_yolo) == len(paths)

    df = pd.DataFrame({
        "embedding_idx": np.arange(len(paths)),
        "path": paths.astype(str),
    })

    print(df.head())
    print(df.shape)


    db_name = "bets_post_mp"

    path_to_channel = {}

    for collection in get_all_collections_name_mongo(db_name):
        channel = get_collection_mongo(collection, db_name)

        query = {
            "kind": "youtube#video",
            "thumbnail_path": {"$exists": True}
        }

        cursor = channel.find(query).batch_size(100)

        for doc in cursor:

            channel_name = doc["snippet"]["channelTitle"]
            path = doc["thumbnail_path"]

            path_to_channel[path] = channel_name

    df["channel"] = df["path"].map(path_to_channel)

    print(df.head())

    print("Total:", len(df))
    print("Com canal:", df["channel"].notna().sum())
    print("Sem canal:", df["channel"].isna().sum())

    df.to_parquet("embeddings_to_channel_guide.parquet", index=False)

def main():
    pass


if __name__ == "__main__":
    main()
