import os
import sys
import cv2
import numpy as np
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

from tqdm import tqdm
from pandas import DataFrame
from scipy.stats import wilcoxon

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Apoio.my_mongo import close_connection, get_all_collections_name_mongo, get_collection_mongo


DATABASE = "Hijacked"
OUTPUT = "./Color_statistics_with_shorts_filter"
REMAKE = True

os.makedirs(OUTPUT, exist_ok=True)

drop_set = {
    "Blindagem Digital- Mindset",
    "SaccaGames™",
    "Edson marsoleto",
    "Caçador de Falhas",
    "Max Willian"
}


def extrair_caracteristicas(caminho: str) -> dict:
    img = cv2.imread(caminho)

    if img is None:
        return None

    # RGB
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    # Redimensiona preservando a proporção
    altura, largura = img.shape[:2]
    escala = min(1.0, 256 / max(altura, largura))

    if escala < 1:
        img = cv2.resize(
            img,
            None,
            fx=escala,
            fy=escala,
            interpolation=cv2.INTER_AREA
        )

    # HSV normalizado
    hsv = cv2.cvtColor(img, cv2.COLOR_RGB2HSV)

    # Valores RGB
    pixels = img.reshape(-1, 3)

    resultado = {}

    for i, canal in enumerate(["R", "G", "B"]):
        resultado[f"{canal}_media"] = np.mean(pixels[:, i])
        resultado[f"{canal}_std"] = np.std(pixels[:, i])

    # Saturação e brilho
    saturacao = hsv[:, :, 1] / 255.0
    brilho = hsv[:, :, 2] / 255.0

    resultado["saturacao_media"] = saturacao.mean()
    resultado["saturacao_std"] = saturacao.std()

    resultado["brilho_medio"] = brilho.mean()
    resultado["brilho_std"] = brilho.std()

    # Proporção de pixels muito saturados
    resultado["alta_saturacao"] = np.mean(
        saturacao >= 0.7
    )

    # Entropia de um histograma RGB conjunto (8x8x8)
    hist, _ = np.histogramdd(
        pixels,
        bins=(8, 8, 8),
        range=((0, 256), (0, 256), (0, 256))
    )

    prob = hist.ravel()
    prob = prob / prob.sum()
    prob = prob[prob > 0]

    resultado["entropia_cores"] = -np.sum(
        prob * np.log2(prob)
    )

    return resultado

def pipeline() -> DataFrame:
    dados = []
    ignoradas = 0

    try:
        for collection_name in tqdm(
            get_all_collections_name_mongo(DATABASE),
            "Extraindo características...",
            total=len(get_all_collections_name_mongo(DATABASE))
        ):

            if collection_name in drop_set:
                continue

            collection = get_collection_mongo(
                collection_name, DATABASE
            )

            cursor = collection.find(
                {"kind": "youtube#video"},
                {
                    "id": 1,
                    "dataset": 1,
                    "thumbnail_path": 1
                }
            )

            for doc in cursor:

                dataset = doc.get("dataset")

                if dataset not in ("regular", "gambling"):
                    continue
                if dataset == "gambling":
                    if doc.get("video_type", "Regular") == "Shorts":
                        continue 

                thumbnail_path = doc.get("thumbnail_path")

                if not thumbnail_path:
                    ignoradas += 1
                    continue

                caminho = thumbnail_path

                if not os.path.isfile(caminho):
                    ignoradas += 1
                    continue

                caracteristicas = extrair_caracteristicas(caminho)

                if caracteristicas is None:
                    ignoradas += 1
                    continue

                caracteristicas.update({
                    "collection": collection_name,
                    "video_id": doc.get("id"),
                    "dataset": dataset,
                    "thumbnail_path": caminho
                })

                dados.append(caracteristicas)

    finally:
        close_connection()

    df = pd.DataFrame(dados)

    if df.empty:
        raise RuntimeError("Nenhuma thumbnail foi processada.")

    df.to_csv(
        f"{OUTPUT}/caracteristicas.csv",
        sep=";",
        index=False
    )

    print("Imagens processadas:", len(df))
    print("Imagens ignoradas:", ignoradas)
    print(df.groupby("dataset").size())

    return df

def plot_global(df: DataFrame) -> None:

    metricas = {
        "saturacao_media": "Saturação média",
        "brilho_medio": "Brilho médio",
        "alta_saturacao": "Proporção de pixels saturados",
        "entropia_cores": "Entropia de cores",
        "R_media": "Vermelho",
        "G_media": "Verde",
        "B_media": "Azul"
    }

    fig, axs = plt.subplots(4, 2, figsize=(15, 17))

    for ax, (metrica, nome) in zip(axs.flat, metricas.items()):

        sns.boxplot(
            data=df,
            x="dataset",
            y=metrica,
            order=["regular", "gambling"],
            showfliers=False,
            ax=ax
        )

        ax.set_title(nome)
        ax.set_xlabel("")
        ax.set_ylabel(nome)
        ax.grid(axis="y", alpha=0.3)

    # Remove o último eixo não utilizado
    fig.delaxes(axs.flat[-1])

    plt.tight_layout()
    plt.savefig(
        f"{OUTPUT}/comparacao_global.png",
        dpi=300
    )
    plt.show()

def plot_group(df: DataFrame) -> None:

    metricas = [
        "saturacao_media",
        "brilho_medio",
        "alta_saturacao",
        "entropia_cores"
    ]

    comparacao = (
        df.groupby(["collection", "dataset"])[metricas]
        .mean()
        .unstack("dataset")
    )

    # Considera somente canais com os dois datasets
    comparacao = comparacao.dropna()

    for metrica in metricas:

        diferenca = (
            comparacao[(metrica, "gambling")] -
            comparacao[(metrica, "regular")]
        )

        diferenca = diferenca.sort_values()

        plt.figure(figsize=(14, 6))

        plt.barh(
            diferenca.index,
            diferenca.values
        )

        plt.axvline(0, color="black")

        plt.title(f"Diferença de {metrica}: Gambling - Regular")
        plt.xlabel("Diferença entre as médias")
        plt.ylabel("Canal")
        plt.grid(axis="x", alpha=0.3)

        plt.tight_layout()
        plt.savefig(
            f"{OUTPUT}/diferenca_{metrica}.png",
            dpi=300
        )
        plt.show()

def histograma_rgb(caminho: str, bins=32) -> np.ndarray:
    img = cv2.imread(caminho)

    if img is None:
        return None

    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    histogramas = []

    for canal in range(3):
        hist, _ = np.histogram(
            img[:, :, canal],
            bins=bins,
            range=(0, 256),
            density=False
        )

        hist = hist.astype(float)
        hist /= hist.sum()
        histogramas.append(hist)

    return np.array(histogramas)

def plot_hist(df: DataFrame) -> None:
    histogramas = {
        "regular": [],
        "gambling": []
    }

    for _, linha in tqdm(
        df.iterrows(),
        "Processando histograma",
        len(df)
    ):

        hist = histograma_rgb(linha["thumbnail_path"])

        if hist is not None:
            histogramas[linha["dataset"]].append(hist)

    centros = np.linspace(4, 252, 32)

    fig, axs = plt.subplots(1, 3, figsize=(17, 5))

    for dataset in ["regular", "gambling"]:

        if not histogramas[dataset]:
            continue

        hist_medio = np.mean(
            histogramas[dataset],
            axis=0
        )

        for i, canal in enumerate(["R", "G", "B"]):

            axs[i].plot(
                centros,
                hist_medio[i],
                label=dataset,
                linewidth=2
            )

            axs[i].set_title(f"Canal {canal}")
            axs[i].set_xlabel("Intensidade")
            axs[i].set_ylabel("Frequência relativa")
            axs[i].legend()
            axs[i].grid(alpha=0.3)

    plt.tight_layout()
    plt.savefig(
        f"{OUTPUT}/histogramas_rgb.png",
        dpi=300
    )
    plt.show()

def teste(df: DataFrame) -> None:
    resumo = (
        df.groupby(["collection", "dataset"])["saturacao_media"]
        .mean()
        .unstack("dataset")
        .dropna(subset=["regular", "gambling"])
    )

    diferencas = resumo["gambling"] - resumo["regular"]

    print("Canais comparados:", len(diferencas))
    print("Diferença média:", diferencas.mean())
    print("Diferença mediana:", diferencas.median())

    if len(diferencas) >= 2 and (diferencas != 0).any():
        estatistica, p_valor = wilcoxon(diferencas)

        print("Estatística:", estatistica)
        print("p-valor:", p_valor)
    else:
        print("Dados insuficientes para o teste.")

def main():

    if not os.path.isfile(f"{OUTPUT}/caracteristicas.csv") or REMAKE:
        data_df = pipeline()
    else:
        data_df = pd.read_csv(f"{OUTPUT}/caracteristicas.csv", sep=";")
    plot_global(data_df)
    plot_group(data_df)
    plot_hist(data_df)
    teste(data_df)


if __name__ == "__main__":
    main()
