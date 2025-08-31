"""Dick business logic and raw data generation service."""

import random
from io import BytesIO
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
from plugins.fun.dick.constants import (
    AVG_GIRTH_ERECT,
    AVG_GIRTH_FLACCID,
    AVG_LENGTH_ERECT,
    AVG_LENGTH_FLACCID,
    STD_GIRTH_ERECT,
    STD_GIRTH_FLACCID,
    STD_LENGTH_ERECT,
    STD_LENGTH_FLACCID,
)


def calculate_dong_attributes() -> dict[str, Any]:
    """Calculates all raw dick attributes and returns them as a dictionary."""

    def generate_normal(
        avg: float, std: float, min_val: float, max_val: float
    ) -> float:
        return max(min_val, min(max_val, random.gauss(avg, std)))

    length_erect = generate_normal(AVG_LENGTH_ERECT, STD_LENGTH_ERECT, 12, 25)
    girth_erect = generate_normal(AVG_GIRTH_ERECT, STD_GIRTH_ERECT, 8, 17)
    length_flaccid = generate_normal(AVG_LENGTH_FLACCID, STD_LENGTH_FLACCID, 5, 15)
    girth_flaccid = generate_normal(AVG_GIRTH_FLACCID, STD_GIRTH_FLACCID, 6, 13)

    volume_erect = np.pi * (girth_erect / (2 * np.pi)) ** 2 * length_erect
    volume_flaccid = np.pi * (girth_flaccid / (2 * np.pi)) ** 2 * length_flaccid

    rigidity = random.uniform(0, 100)
    stamina = random.uniform(1, 60)
    sensitivity = random.uniform(1, 10)

    satisfaction_rating = calculate_satisfaction_rating(
        length_erect, girth_erect, rigidity, stamina, sensitivity
    )

    return {
        "length_erect": length_erect,
        "girth_erect": girth_erect,
        "volume_erect": volume_erect,
        "length_flaccid": length_flaccid,
        "girth_flaccid": girth_flaccid,
        "volume_flaccid": volume_flaccid,
        "rigidity": rigidity,
        "curvature": random.uniform(-30, 30),
        "velocity": random.uniform(0, 30),
        "stamina": stamina,
        "refractory_period": random.uniform(5, 120),
        "sensitivity": sensitivity,
        "satisfaction_rating": satisfaction_rating,
    }


def calculate_satisfaction_rating(
    length: float, girth: float, rigidity: float, stamina: float, sensitivity: float
) -> float:
    """Calculates the satisfaction rating based on attributes and returns the raw percentage."""
    length_score = min(max((length - 13) / 5, 0), 2)
    girth_score = min(max((girth - 10) / 3, 0), 2)
    rigidity_score = rigidity / 50
    stamina_score = min(stamina / 15, 2)
    sensitivity_score = 2 - abs(5 - sensitivity) / 2.5

    total_score = (
        length_score + girth_score + rigidity_score + stamina_score + sensitivity_score
    )
    rating = total_score / 10 * 100
    return rating


def plot_attributes(attributes: dict[str, Any]) -> BytesIO:
    fig = plt.figure(figsize=(16, 16))
    fig.suptitle("Атрибуты пениса", fontsize=16)
    ax_radar = fig.add_subplot(221, projection="polar")
    labels = [
        "Длина",
        "Обхват",
        "Жёсткость",
        "Выносливость",
        "Чувствительность",
        "Скорость",
        "Удовлетворение",
    ]
    stats = [
        attributes["length_erect"],
        attributes["girth_erect"],
        attributes["rigidity"],
        attributes["stamina"],
        attributes["sensitivity"],
        attributes["velocity"],
        attributes["satisfaction_rating"],
    ]
    max_values = [25, 17, 100, 60, 10, 30, 100]
    stats = [stat / max_val * 10 for stat, max_val in zip(stats, max_values, strict=False)]
    angles = np.linspace(0, 2 * np.pi, len(labels), endpoint=False)
    stats = np.concatenate((stats, [stats[0]]))
    angles = np.concatenate((angles, [angles[0]]))
    ax_radar.plot(angles, stats, "o-", linewidth=2)
    ax_radar.fill(angles, stats, alpha=0.25)
    ax_radar.set_xticks(angles[:-1])
    ax_radar.set_xticklabels(labels)
    ax_radar.set_ylim(0, 10)
    ax_radar.set_title("Радар атрибутов")
    for label, angle in zip(ax_radar.get_xticklabels(), angles, strict=False):
        if angle in (0, np.pi):
            label.set_horizontalalignment("center")
        elif 0 < angle < np.pi:
            label.set_horizontalalignment("left")
        else:
            label.set_horizontalalignment("right")
    ax_radar.set_yticks(range(1, 11))
    ax_radar.set_yticklabels([])
    for y in range(1, 11):
        ax_radar.text(
            np.deg2rad(180 / len(labels)), y, str(y), ha="center", va="center"
        )
    ax_hist = fig.add_subplot(222)
    lengths = np.random.normal(AVG_LENGTH_ERECT, STD_LENGTH_ERECT, 1000)
    ax_hist.hist(lengths, bins=30, alpha=0.7, color="skyblue", edgecolor="black")
    ax_hist.axvline(
        attributes["length_erect"], color="red", linestyle="dashed", linewidth=2
    )
    ax_hist.set_xlabel("Длина (см)")
    ax_hist.set_ylabel("Частота")
    ax_hist.set_title("Распределение длины")
    ax_scatter = fig.add_subplot(223)
    lengths = np.random.normal(AVG_LENGTH_ERECT, STD_LENGTH_ERECT, 1000)
    girths = np.random.normal(AVG_GIRTH_ERECT, STD_GIRTH_ERECT, 1000)
    ax_scatter.scatter(lengths, girths, alpha=0.5)
    ax_scatter.scatter(
        attributes["length_erect"],
        attributes["girth_erect"],
        color="red",
        s=100,
        marker="*",
    )
    ax_scatter.set_xlabel("Длина (см)")
    ax_scatter.set_ylabel("Обхват (см)")
    ax_scatter.set_title("Длина vs Обхват")
    ax_bar = fig.add_subplot(224)
    factors = ["Длина", "Обхват", "Жёсткость", "Выносливость", "Чувствительность"]
    values = [
        min(max((attributes["length_erect"] - 13) / 5, 0), 2),
        min(max((attributes["girth_erect"] - 10) / 3, 0), 2),
        attributes["rigidity"] / 50,
        min(attributes["stamina"] / 15, 2),
        2 - abs(5 - attributes["sensitivity"]) / 2.5,
    ]
    ax_bar.bar(factors, values)
    ax_bar.set_ylim(0, 2)
    ax_bar.set_ylabel("Вклад в удовлетворение")
    ax_bar.set_title("Факторы удовлетворения")
    plt.tight_layout()
    image_buffer = BytesIO()
    fig.savefig(image_buffer, format="png")
    image_buffer.seek(0)
    plt.close(fig)
    return image_buffer
