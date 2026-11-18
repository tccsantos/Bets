import os
import sys
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Apoio.my_mongo import close_connection, get_all_collections_name_mongo, get_collection_mongo, data_save_mongo

dados = []

drop_set = {"Blindagem Digital- Mindset", "SaccaGames™", "Edson marsoleto", "Caçador de Falhas", "Max Willian"}

for collection_name in get_all_collections_name_mongo("Hijacked"):

    if collection_name in drop_set:
        continue

    collection = get_collection_mongo(collection_name, "Hijacked")

    for doc in collection.find({"kind": "youtube#video"}):

        snippet = doc.get("snippet", {})
        stats = doc.get("statistics", {})

        info = {
            "collection": collection_name,
            "video_id": doc.get("id"),
            "dataset": doc.get("dataset", "regular"),
            "publishedAt": snippet.get("publishedAt"),
            "type": doc.get("video_type", "Desconhecido"),

            "views": int(stats.get("viewCount", 0)),
            "likes": int(stats.get("likeCount", 0)),
            "comments": int(stats.get("commentCount", 0))
        }

        if grupo := doc.get("grupo"):
            info["grupo"] = int(grupo)

        dados.append(info)

df = pd.DataFrame(dados)
df.to_csv("./roubados_without_shorts.csv", sep=";")
sys.exit(0)


df["publishedAt"] = pd.to_datetime(df["publishedAt"])
df = df.sort_values("publishedAt")

metricas = ["views", "likes", "comments"]

labels_metricas = {
    "views": "Visualizações",
    "comments": "Comentários",
    "likes": "Likes"
}

labels_content = {
    "regular": "Conteúdo original",
    "gambling": "Conteúdo de apostas"
}

# df["grupo"] = (
#     df.groupby("collection")["grupo"]
#       .transform(lambda s: s.dropna().iloc[0] if not s.dropna().empty else None)
# )

plt.rcParams.update({
        "font.size": 24,        # fonte padrão
        "axes.titlesize": 24,   # título
        "axes.labelsize": 22,   # nomes dos eixos
        "xtick.labelsize": 20,  # números do eixo X
        "ytick.labelsize": 20,  # números do eixo Y
        "legend.fontsize": 20   # legenda
    })

print(df.head())


fig, axs = plt.subplots(3, 1, figsize=(15, 14))

for ax, metrica in zip(axs, metricas):

    for dataset in ["regular", "gambling"]:

        temp = (
            df[df.dataset == dataset]
            .sort_values("publishedAt")
            .copy()
        )

        ax.scatter(
            temp["publishedAt"],
            temp[metrica],
            alpha=0.35
        )

        media = (
            temp
            .set_index("publishedAt")[metrica]
            .rolling("30D")
            .mean()
        )

        ax.plot(
            media.index,
            media.values,
            linewidth=3,
            label=labels_content.get(dataset)
        )

    ax.set_title(f"{metrica.capitalize()} - Todas as collections")
    ax.grid(True)
    ax.legend()

plt.tight_layout()
plt.show()


for collection in sorted(df.collection.unique()):

    subset = (
        df[df.collection == collection]
        .sort_values("publishedAt")
    )

    fig, axs = plt.subplots(3, 1, figsize=(14, 12))

    for ax, metrica in zip(axs, metricas):

        for dataset in ["regular", "gambling"]:

            temp = subset[
                subset.dataset == dataset
            ]

            ax.plot(
                temp["publishedAt"],
                temp[metrica],
                marker="o",
                linewidth=2,
                label=dataset
            )

        ax.set_title(f"{collection} - {metrica}")
        ax.grid(True)
        ax.legend()

    plt.tight_layout()
    plt.show()

    # for metrica in metricas:

    #     fig, ax = plt.subplots(figsize=(14, 4))

    #     for dataset in ["regular", "gambling"]:

    #         temp = subset[
    #             subset.dataset == dataset
    #         ]

    #         ax.plot(
    #             temp["publishedAt"],
    #             temp[metrica],
    #             marker="o",
    #             linewidth=2,
    #             label=labels_content.get(dataset),
    #         )

    #     ax.set_title(f"Canal: {collection} - Número de {labels_metricas.get(metrica)}")
    #     ax.set_xlabel("Data de publicação")
    #     ax.set_ylabel(labels_metricas.get(metrica))
    #     ax.grid(True)
    #     ax.legend()

    #     plt.tight_layout()
    #     plt.show()

comparacao = (
    df.groupby(["collection", "dataset"])
      .agg(
          views=("views", "mean"),
          likes=("likes", "mean"),
          comments=("comments", "mean"),
          publishedAt=("publishedAt", "min"),
        #   grupo=("grupo", "first")
      )
      .reset_index()
)

pivot = comparacao.pivot(
    index="collection",
    columns="dataset"
)

pivot.columns = [
    f"{a}_{b}"
    for a, b in pivot.columns
]

# grupo_por_canal = (
#     df.groupby("collection")["grupo"]
#       .first()
# )

# pivot["grupo"] = pivot.index.map(grupo_por_canal)

pivot = pivot.reset_index()


for metrica in metricas:

    pivot[f"{metrica}_diff"] = (
        pivot[f"{metrica}_gambling"] -
        pivot[f"{metrica}_regular"]
    )

    pivot[f"{metrica}_ratio"] = (
        pivot[f"{metrica}_gambling"] /
        pivot[f"{metrica}_regular"]
    )

    pivot[f"{metrica}_pct_change"] = (
        (pivot[f"{metrica}_gambling"] /
        pivot[f"{metrica}_regular"] - 1) * 100
    )

pivot = pivot.sort_values("publishedAt_regular")

fig, axs = plt.subplots(3, 1, figsize=(15, 14))

for ax, metrica in zip(axs, metricas):

    ax.bar(
        pivot["collection"],
        pivot[f"{metrica}_diff"]
    )

    ax.axhline(0, color="black")

    ax.set_title(f"{metrica.capitalize()} - Gambling - Regular")
    ax.set_ylabel("Diferença")
    ax.tick_params(axis='x', rotation=45)
    ax.grid(True)

plt.tight_layout()
plt.show()


mapa_grupos = {
    0: 0,
    1: 1,
    2: 2,
    3: 3,
    4: 4,
    5: 4,
    6: 4
}


nomes_grupos = {
    0: "Canais que mantiveram seus criadores originais",
    1: "Grupo com 8 influenciadores",
    2: "Grupo com 1 influenciadores",
    3: "Grupo com 2 influenciadores",
    4: "Grupos que controlam somente 1 canal"
}


cores = {
    0: "tab:blue",
    1: "tab:orange",
    2: "tab:green",
    3: "tab:red",
    4: "tab:purple"
}


# pivot["grupo_plot"] = pivot["grupo"].map(mapa_grupos)


for metrica in metricas:

    dados = pivot.sort_values(by=f"{metrica}_diff", ascending=True)

    plt.figure(figsize=(15, 4))

    plt.bar(
        dados["collection"],
        dados[f"{metrica}_diff"],
        # color=dados["grupo_plot"].map(cores)
    )

    plt.axhline(0, color="black")

    # legendas = [
    #     Patch(facecolor=cores[g], label=nomes_grupos[g])
    #     for g in sorted(cores)
    # ]

    # plt.legend(handles=legendas, title="Grupos", loc="lower right")

    plt.title(f"Variação das {labels_metricas.get(metrica).capitalize()} entre o conteúdo original e o conteúdo de apostas em números absolutos")
    plt.ylabel("Diferença absoluta")
    plt.xticks(rotation=45)
    plt.grid(True)

    plt.tight_layout()
    plt.show()



for metrica in metricas:

    dados = pivot.sort_values(by=f"{metrica}_pct_change", ascending=True)

    plt.figure(figsize=(15, 4))

    plt.bar(
        dados["collection"],
        dados[f"{metrica}_pct_change"],
        # color=dados["grupo_plot"].map(cores)
    )

    plt.axhline(0, color="black")

    # legendas = [
    #     Patch(facecolor=cores[g], label=nomes_grupos[g])
    #     for g in sorted(cores)
    # ]

    # plt.legend(handles=legendas, title="Grupo", loc="upper left")

    plt.title(f"Variação das {labels_metricas.get(metrica).capitalize()} entre o conteúdo original e o conteúdo de apostas proporcional ao conteúdo original")
    plt.ylabel("Diferença (%)")
    plt.xticks(rotation=45)
    plt.grid(True)

    plt.tight_layout()
    plt.show()

sys.exit(0)


fig, axs = plt.subplots(3, 1, figsize=(15, 14))

for ax, metrica in zip(axs, metricas):

    ax.plot(
        pivot["collection"],
        pivot[f"{metrica}_ratio"],
        marker="o",
        linewidth=2
    )

    ax.axhline(
        1,
        color="red",
        linestyle="--"
    )

    ax.set_title(f"{metrica.capitalize()} - Gambling / Regular")
    ax.set_ylabel("Razão")
    ax.tick_params(axis='x', rotation=45)
    ax.grid(True)

plt.tight_layout()
plt.show()


fig, axs = plt.subplots(3, 1, figsize=(15, 14))

for ax, metrica in zip(axs, metricas):

    ax.plot(
        pivot["publishedAt_regular"],
        pivot[f"{metrica}_ratio"],
        marker="o",
        linewidth=3
    )

    ax.axhline(
        1,
        color="red",
        linestyle="--"
    )

    ax.set_title(f"{metrica.capitalize()} - Evolução Gambling / Regular")
    ax.set_ylabel("Razão")
    ax.grid(True)

plt.tight_layout()
plt.show()