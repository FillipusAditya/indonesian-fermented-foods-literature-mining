"""Browse the consolidated Indonesian fermented food inventory."""

from __future__ import annotations

from collections import Counter
from html import escape
from pathlib import Path
from urllib.parse import quote

import pandas as pd
import streamlit as st

from i18n import language as current_language


INVENTORY_PATH = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "clear_fermented_food_inventory.csv"
)

CATEGORY_LABELS = {
    "English": {
        "dairy": "Dairy", "vegetable": "Vegetable", "fruit": "Fruit",
        "cereal": "Cereal", "tuber": "Tuber", "legume": "Legume",
        "meat": "Meat", "seafood": "Seafood", "egg": "Egg",
        "plant_sap": "Plant sap",
    },
    "Indonesia": {
        "dairy": "Susu", "vegetable": "Sayuran", "fruit": "Buah",
        "cereal": "Serealia", "tuber": "Umbi", "legume": "Kacang-kacangan",
        "meat": "Daging", "seafood": "Hasil laut", "egg": "Telur",
        "plant_sap": "Nira",
    },
}

TEXT = {
    "English": {
        "eyebrow": "NUSANTARA · FOOD ATLAS",
        "hero_title": "Indonesia Fermentation Product",
        "intro": "Explore the ingredients, fermentation methods, and microorganisms documented across traditional Indonesian foods.",
        "products": "Fermented products",
        "categories": "Fermented product categories",
        "microorganisms": "Identified microorganisms",
        "sources": "Literature resources",
        "explore": "Explore by tradition",
        "explore_sub": "Choose a category or search the collection.",
        "all": "All",
        "search": "Search foods, ingredients, microorganisms or references",
        "search_placeholder": "Try tempe, cassava, or lactobacillus",
        "showing": "Showing {shown} of {total} foods",
        "empty": "No foods match these filters. Try another term or category.",
        "microbe_one": "microorganism",
        "microbe_many": "microorganisms",
        "reference_one": "reference",
        "reference_many": "references",
        "view": "View profile",
        "profile": "Food profile",
        "uncategorized": "Uncategorized",
        "material_missing": "Material not recorded",
        "category_missing": "Category not recorded",
        "ingredients": "Ingredients & Materials",
        "primary": "Primary material",
        "additional": "Additional ingredients",
        "starter": "Starter material",
        "casing": "Casing material",
        "process_section": "Fermentation & Microbiology",
        "process": "Fermentation process",
        "reported_microbes": "Reported microorganisms",
        "literature": "Literature references",
        "not_reported": "Not reported",
        "previous": "← Previous",
        "next": "Next →",
        "page": "Page {page} of {count}",
    },
    "Indonesia": {
        "eyebrow": "NUSANTARA · ATLAS PANGAN",
        "hero_title": "Produk Fermentasi Indonesia",
        "intro": "Jelajahi bahan, proses fermentasi, dan mikroorganisme yang dilaporkan pada pangan fermentasi tradisional Indonesia.",
        "products": "Produk fermentasi",
        "categories": "Kategori produk fermentasi",
        "microorganisms": "Mikroorganisme teridentifikasi",
        "sources": "Sumber literatur",
        "explore": "Jelajahi berdasarkan kategori",
        "explore_sub": "Pilih kategori atau cari dalam koleksi.",
        "all": "Semua",
        "search": "Cari pangan, bahan, mikroorganisme, atau referensi",
        "search_placeholder": "Contoh: tempe, singkong, atau lactobacillus",
        "showing": "Menampilkan {shown} dari {total} produk",
        "empty": "Tidak ada produk yang cocok. Coba kata kunci atau kategori lain.",
        "microbe_one": "mikroorganisme",
        "microbe_many": "mikroorganisme",
        "reference_one": "referensi",
        "reference_many": "referensi",
        "view": "Lihat profil",
        "profile": "Profil produk",
        "uncategorized": "Tanpa kategori",
        "material_missing": "Bahan tidak dicatat",
        "category_missing": "Kategori tidak dicatat",
        "ingredients": "Bahan & Komposisi",
        "primary": "Bahan utama",
        "additional": "Bahan tambahan",
        "starter": "Bahan starter",
        "casing": "Bahan pembungkus",
        "process_section": "Fermentasi & Mikrobiologi",
        "process": "Proses fermentasi (teks sumber)",
        "reported_microbes": "Mikroorganisme yang dilaporkan",
        "literature": "Referensi literatur",
        "not_reported": "Tidak dilaporkan",
        "previous": "← Sebelumnya",
        "next": "Berikutnya →",
        "page": "Halaman {page} dari {count}",
    },
}

def split_values(value: str) -> list[str]:
    """Return unique, nonempty semicolon-separated values in source order."""
    values = []
    for item in value.split(";"):
        item = item.strip()
        if item and item not in values:
            values.append(item)
    return values


def load_inventory() -> pd.DataFrame:
    """Read the latest CSV each time the page reruns."""
    return pd.read_csv(INVENTORY_PATH, dtype=str, keep_default_na=False)


def reset_food_page() -> None:
    st.session_state["food_page"] = 1


def select_food(food_id: str) -> None:
    st.session_state["selected_food_id"] = food_id
    st.session_state["scroll_to_food_profile"] = True
    st.session_state["profile_scroll_sequence"] = (
        st.session_state.get("profile_scroll_sequence", 0) + 1
    )


def category_name(category: str, language: str) -> str:
    return CATEGORY_LABELS[language].get(category, category.replace("_", " ").title())


def render_card(food: dict[str, str], language: str) -> None:
    labels = TEXT[language]
    categories = split_values(food["fermented_food_category_en"])
    category_text = " · ".join(category_name(item, language) for item in categories)
    material_column = "primary_material_idn" if language == "Indonesia" else "primary_material_en"
    material = food[material_column] or labels["material_missing"]
    microbe_count = len(split_values(food["existing_microorganism"]))
    reference_count = len(split_values(food["references"]))
    microbe_label = labels["microbe_one" if microbe_count == 1 else "microbe_many"]
    reference_label = labels["reference_one" if reference_count == 1 else "reference_many"]

    with st.container(key=f"food_card_{food['food_id']}"):
        st.markdown(
            f'<div class="food-card-index">{escape(food["food_id"])}</div>'
            f'<div class="food-card-title">{escape(food["fermented_food"].title())}</div>'
            f'<div class="food-card-categories">{escape(category_text or labels["uncategorized"])}</div>'
            f'<div class="food-card-material">{escape(material)}</div>'
            f'<div class="food-card-meta">{microbe_count} {microbe_label} &nbsp; · &nbsp; '
            f'{reference_count} {reference_label}</div>',
            unsafe_allow_html=True,
        )
        st.button(
            labels["view"], key=f"view_{food['food_id']}", width="stretch",
            on_click=select_food, args=(food["food_id"],),
        )


def render_detail_field(label: str, value: str, missing: str) -> None:
    value_class = "detail-value" if value else "detail-value missing"
    content = escape(value) if value else escape(missing)
    st.markdown(
        f'<div class="detail-section">{escape(label)}</div>'
        f'<div class="{value_class}">{content}</div>',
        unsafe_allow_html=True,
    )


def render_detail(food: dict[str, str], language: str) -> None:
    labels = TEXT[language]
    categories = split_values(food["fermented_food_category_en"])
    category_text = ", ".join(category_name(item, language) for item in categories)
    suffix = "_idn" if language == "Indonesia" else "_en"

    with st.container(key="food_detail"):
        st.markdown(
            f'<div class="detail-kicker">{escape(labels["profile"])}</div>'
            f'<div class="detail-title">{escape(food["fermented_food"].title())}</div>'
            f'<div class="detail-sub">{escape(food["food_id"])} &nbsp; · &nbsp; '
            f'{escape(category_text or labels["category_missing"])}</div>',
            unsafe_allow_html=True,
        )
        ingredients, process = st.columns([1, 1], gap="large")
        with ingredients:
            st.markdown(f'#### {labels["ingredients"]}')
            for key, column in (
                ("primary", "primary_material"),
                ("additional", "additional_ingredients"),
                ("starter", "starter_material"),
                ("casing", "casing_material"),
            ):
                render_detail_field(
                    labels[key], food[column + suffix], labels["not_reported"]
                )
        with process:
            st.markdown(f'#### {labels["process_section"]}')
            render_detail_field(
                labels["process"], food["fermentation_process"], labels["not_reported"]
            )
            microbes = split_values(food["existing_microorganism"])
            st.markdown(
                f'<div class="detail-section">{escape(labels["reported_microbes"])}</div>',
                unsafe_allow_html=True,
            )
            if microbes:
                tags = "".join(
                    f'<span class="microbe-tag">{escape(name)}</span>' for name in microbes
                )
                st.markdown(tags, unsafe_allow_html=True)
            else:
                st.markdown(
                    f'<div class="detail-value missing">{escape(labels["not_reported"])}</div>',
                    unsafe_allow_html=True,
                )

            st.markdown(
                f'<div class="detail-section">{escape(labels["literature"])}</div>',
                unsafe_allow_html=True,
            )
            references = split_values(food["references"])
            if references:
                links = "".join(
                    f'<a class="doi-link" href="https://doi.org/{quote(doi, safe="/.")}" '
                    f'target="_blank" rel="noopener noreferrer">{escape(doi)} ↗</a>'
                    for doi in references
                )
                st.markdown(links, unsafe_allow_html=True)
            else:
                st.markdown(
                    f'<div class="detail-value missing">{escape(labels["not_reported"])}</div>',
                    unsafe_allow_html=True,
                )


def render_food_inventory() -> None:
    if not INVENTORY_PATH.exists():
        st.error(
            "The food inventory CSV was not found. Run section 1.5 of "
            "notebooks/main.ipynb to create data/clear_fermented_food_inventory.csv."
        )
        return

    language = current_language()
    labels = TEXT[language]
    inventory = load_inventory()
    foods = inventory.to_dict("records")
    category_counts = Counter(
        category
        for food in foods
        for category in split_values(food["fermented_food_category_en"])
    )
    microorganisms = {
        name
        for food in foods
        for name in split_values(food["existing_microorganism"])
    }
    references = {doi for food in foods for doi in split_values(food["references"])}

    st.markdown(
        '<div class="atlas-hero">'
        f'<div class="atlas-eyebrow">{escape(labels["eyebrow"])}</div>'
        f'<div class="atlas-title">{labels["hero_title"]}</div>'
        f'<p class="atlas-intro">{escape(labels["intro"])}</p>'
        f'<div class="atlas-seal"><strong>{len(foods)}</strong><span>{escape(labels["products"]).upper()}</span></div>'
        '</div>',
        unsafe_allow_html=True,
    )
    stats = (
        (len(foods), labels["products"]),
        (len(category_counts), labels["categories"]),
        (len(microorganisms), labels["microorganisms"]),
        (len(references), labels["sources"]),
    )
    st.markdown(
        '<div class="atlas-stats">'
        + "".join(
            f'<div class="atlas-stat"><strong>{count}</strong><span>{escape(label)}</span></div>'
            for count, label in stats
        )
        + '</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="atlas-section-title">{escape(labels["explore"])}</div>'
        f'<div class="atlas-section-sub">{escape(labels["explore_sub"])}</div>',
        unsafe_allow_html=True,
    )
    category_options = ["all", *(
        category for category, _ in category_counts.most_common()
    )]
    category = st.pills(
        "Category / Kategori", category_options,
        default="all", required=True, wrap=True,
        format_func=lambda item: (
            f'{labels["all"]} · {len(foods)}' if item == "all"
            else f'{category_name(item, language)} · {category_counts[item]}'
        ),
        key="food_category_filter", label_visibility="collapsed",
        on_change=reset_food_page,
    ) or "all"
    query = st.text_input(
        labels["search"], placeholder=labels["search_placeholder"],
        key="food_search", on_change=reset_food_page,
    ).strip().casefold()

    filtered = []
    for food in foods:
        if category != "all" and category not in split_values(
            food["fermented_food_category_en"]
        ):
            continue
        searchable = " ".join(
            food[column]
            for column in (
                "fermented_food", "primary_material_en", "primary_material_idn",
                "additional_ingredients_en", "additional_ingredients_idn",
                "starter_material_en", "starter_material_idn",
                "casing_material_en", "casing_material_idn",
                "fermentation_process", "existing_microorganism", "references",
            )
        ).casefold()
        if query and query not in searchable:
            continue
        filtered.append(food)
    filtered.sort(key=lambda food: food["fermented_food"].casefold())

    st.markdown(
        f'<div class="atlas-results-count">'
        f'{escape(labels["showing"].format(shown=len(filtered), total=len(foods)))}'
        '</div>',
        unsafe_allow_html=True,
    )
    if not filtered:
        st.info(labels["empty"])
        return

    page_count = (len(filtered) + 8) // 9
    page = min(max(st.session_state.get("food_page", 1), 1), page_count)
    st.session_state["food_page"] = page
    visible = filtered[(page - 1) * 9:page * 9]
    selected_id = st.session_state.get("selected_food_id")
    selected_food = next(
        (food for food in visible if food["food_id"] == selected_id), visible[0]
    )
    for start in range(0, len(visible), 3):
        row = visible[start:start + 3]
        columns = st.columns(3, gap="medium")
        for column, food in zip(columns, row):
            with column:
                render_card(food, language)

    if page_count > 1:
        with st.container(key="food_pagination"):
            previous, indicator, next_page = st.columns([1, 1.3, 1])
            with previous:
                if st.button(labels["previous"], disabled=page == 1, width="stretch"):
                    st.session_state["food_page"] = page - 1
                    st.rerun()
            with indicator:
                st.markdown(
                    f'<div class="atlas-pager">{labels["page"].format(page=page, count=page_count)}</div>',
                    unsafe_allow_html=True,
                )
            with next_page:
                if st.button(labels["next"], disabled=page == page_count, width="stretch"):
                    st.session_state["food_page"] = page + 1
                    st.rerun()

    st.markdown(
        f'<div class="atlas-section-title">{escape(labels["profile"])}</div>',
        unsafe_allow_html=True,
    )
    render_detail(selected_food, language)
    if st.session_state.pop("scroll_to_food_profile", False):
        st.html(
            f"<script>/* click {st.session_state['profile_scroll_sequence']} */ "
            "requestAnimationFrame(() => "
            "document.querySelector('.st-key-food_detail')?.scrollIntoView("
            "{behavior: 'smooth', block: 'start'}));</script>",
            unsafe_allow_javascript=True,
        )

