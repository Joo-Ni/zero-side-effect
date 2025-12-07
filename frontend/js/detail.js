const detailName = document.getElementById("detail-product-name");
const detailTags = document.getElementById("detail-sweetener-tags");
const detailNutritionTable = document.getElementById("detail-nutrition-table");

async function initDetailPage() {
  try {
    const id = getQueryParam("id");
    if (!id) {
      detailName.textContent = "제품 정보가 존재하지 않습니다.";
      return;
    }

    const [prodFull, cats, sweets] = await Promise.all([
      fetchJSON(`${API_BASE}/products/${id}/full`),
      fetchJSON(`${API_BASE}/categories`),
      fetchJSON(`${API_BASE}/sweeteners`),
    ]);

    const sweetNames = ["알룰로오스", "에리스리톨", "당알코올"];
    initGlobalNav("products", cats, sweetNames);

    fillDetail(prodFull);
  } catch (err) {
    console.error("상세 페이지 로딩 실패:", err);
    detailName.textContent = "제품 정보를 불러오는 데 실패했습니다.";
  }
}

function fillDetail(prod) {
  const img = document.getElementById("detail-product-img");

  if (img) {
    if (prod.image_url) {
      img.src = `http://127.0.0.1:8000${prod.image_url}`;
    } else {
      img.src = "assets/no-image.png";
    }
  }

  detailName.textContent = prod.name || "";

  detailTags.innerHTML = "";
  (prod.sweeteners || []).forEach((s) => {
    const name = s.name || s;
    const tag = document.createElement("span");
    tag.className = "zse-tag " + getSweetenerTagClass(name);
    tag.textContent = name;
    detailTags.appendChild(tag);
  });

  detailNutritionTable.innerHTML = "";
  const nf = prod.nutrition || {};
  const rows = [
    { label: "에너지", value: nf.kcal != null ? `${nf.kcal} kcal` : "-" },
    {
      label: "탄수화물",
      value: nf.carbohydrate_g != null ? `${nf.carbohydrate_g} g` : "-",
    },
    { label: "당류", value: nf.sugar_g != null ? `${nf.sugar_g} g` : "-" },
    { label: "지방", value: nf.fat_g != null ? `${nf.fat_g} g` : "-" },
    {
      label: "포화지방",
      value: nf.saturated_fat_g != null ? `${nf.saturated_fat_g} g` : "-",
    },
    {
      label: "트랜스지방",
      value: nf.trans_fat_g != null ? `${nf.trans_fat_g} g` : "-",
    },
    {
      label: "단백질",
      value: nf.protein_g != null ? `${nf.protein_g} g` : "-",
    },
    {
      label: "나트륨",
      value: nf.sodium_mg != null ? `${nf.sodium_mg} mg` : "-",
    },
  ];

  rows.forEach((r) => {
    const rowEl = document.createElement("div");
    rowEl.className = "zse-nutrition-row";

    const label = document.createElement("span");
    label.textContent = r.label;

    const val = document.createElement("span");
    val.textContent = r.value;

    rowEl.appendChild(label);
    rowEl.appendChild(val);
    detailNutritionTable.appendChild(rowEl);
  });
}

window.addEventListener("DOMContentLoaded", initDetailPage);
