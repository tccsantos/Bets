import numpy as np
import pandas as pd

from xgboost import XGBClassifier
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score, f1_score
from sklearn.model_selection import StratifiedKFold, StratifiedGroupKFold, LeaveOneGroupOut, cross_val_score

def get_data():
    df_original = pd.read_parquet("./Parquets/embeddings_to_channel_guide_sequestro.parquet")
    
    embeddings_clip_original = np.load("./AI/embeddings_clip.npy")
    embeddings_resnet_original = np.load("./AI/embeddings_resnet.npy")

    # Índices dos embeddings que pertencem ao DataFrame
    indices = df_original["embedding_idx"].to_numpy()

    # Seleciona somente os embeddings presentes no DF
    embeddings_clip = embeddings_clip_original[indices]
    embeddings_resnet = embeddings_resnet_original[indices]

    print("Embeddings CLIP selecionados:", embeddings_clip.shape)
    print("Embeddings ResNet selecionados:", embeddings_resnet.shape)
    print("DataFrame:", df_original.shape)

    assert len(df_original) == len(embeddings_clip)
    assert len(df_original) == len(embeddings_resnet)

    return df_original, embeddings_clip, embeddings_resnet

def set_data():

    df, embeddings_clip, embeddings_resnet = get_data()

    # indices = df["embedding_idx"].to_numpy()

    # embeddings_clip = embeddings_clip[indices]
    # embeddings_resnet = embeddings_resnet[indices]

    # Target
    y = df["sequestro"].astype(int).to_numpy()

    groups = df["channel"].to_numpy()

    print("CLIP:", embeddings_clip.shape)
    print("ResNet:", embeddings_resnet.shape)
    print("Target:", y.shape)
    print("\nDistribuição das classes:")
    print(pd.Series(y).value_counts())
    print("Canais:")
    print(df["channel"].value_counts())

    print("\nClasses:")
    print(df["sequestro"].value_counts())

    model = XGBClassifier(
        n_estimators=300,
        max_depth=6,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        objective="binary:logistic",
        eval_metric="logloss",
        random_state=42,
        n_jobs=-1
    )


    # cv = StratifiedKFold(
    #     n_splits=10,
    #     shuffle=True,
    #     random_state=42
    # )

    # cv = StratifiedGroupKFold(
    #     n_splits=6,
    #     shuffle=True,
    #     random_state=42
    # )

    cv = LeaveOneGroupOut()

    return embeddings_clip, embeddings_resnet, y, model, cv, groups

def evaluate_logo(X, y, groups, model):

    logo = LeaveOneGroupOut()
    results = []

    for fold, (train_idx, test_idx) in enumerate(
        logo.split(X, y, groups),
        start=1
    ):
        test_channel = groups[test_idx][0]

        model.fit(X[train_idx], y[train_idx])

        y_pred = model.predict(X[test_idx])

        f1 = f1_score(
            y[test_idx],
            y_pred,
            average="weighted"
        )

        results.append({
            "fold": fold,
            "channel": test_channel,
            "n_train": len(train_idx),
            "n_test": len(test_idx),
            "class_0": np.sum(y[test_idx] == 0),
            "class_1": np.sum(y[test_idx] == 1),
            "f1_weighted": f1
        })

    return pd.DataFrame(results)

def evaluate_embedding(name, X, y, model, cv, groups):

    scores = cross_val_score(
        model,
        X,
        y,
        cv=cv,
        groups=groups,
        scoring="f1_weighted",
        n_jobs=-1
    )

    print(f"\n{name}")
    print("-" * 40)

    for i, score in enumerate(scores, start=1):
        print(f"Fold {i:02d}: {score:.4f}")

    print(f"\nF1 médio: {scores.mean():.4f}")
    print(f"Desvio padrão: {scores.std():.4f}")

    return scores

def pipeline():

    embeddings_clip, embeddings_resnet, y, model, cv, groups = set_data()

    # scores_clip = evaluate_embedding(
    #     "CLIP",
    #     embeddings_clip,
    #     y,
    #     model,
    #     cv,
    #     groups
    # )

    # scores_resnet = evaluate_embedding(
    #     "ResNet",
    #     embeddings_resnet,
    #     y,
    #     model,
    #     cv,
    #     groups
    # )

    results_clip = evaluate_logo(
        embeddings_clip,
        y,
        groups,
        model
    )

    results_resnet = evaluate_logo(
        embeddings_resnet,
        y,
        groups,
        model
    )

    # print("CLIP")
    # print("Folds:", scores_clip)
    # print(f"Média: {scores_clip.mean():.4f}")
    # print(f"Desvio padrão: {scores_clip.std():.4f}")

    # print("\nResNet")
    # print("Folds:", scores_resnet)
    # print(f"Média: {scores_resnet.mean():.4f}")
    # print(f"Desvio padrão: {scores_resnet.std():.4f}")

    print("CLIP")
    print(results_clip.to_string(index=False))

    print("\nResNet")
    print(results_resnet.to_string(index=False))

def main():
    pipeline()


if __name__ == "__main__":
    main()
