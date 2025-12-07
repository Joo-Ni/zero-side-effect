let allProducts_sw = [];
let categories_sw = [];
let sweeteners_sw = [];

const swTitle = document.getElementById("sweetener-title");
const swDesc = document.getElementById("sweetener-desc");
const swGrid = document.getElementById("product-grid");
const swEmpty = document.getElementById("empty-message");

const sweetenerDescriptions = {
  알룰로오스:
    "과도 섭취 시 일시적인 설사, 복통이 발생할 수 있습니다. 일반적으로는 안전한 편이지만, 단기간 과섭취는 장에 부담을 줄 수 있습니다.",
  에리스리톨:
    "체내 흡수율이 낮아 비교적 안전한 편이지만, 많게 섭취하면 팽만감이나 설사가 생길 수 있습니다.",
  당알코올:
    "당알코올은 소화 과정에서 설사나 복통을 유발할 수 있고, 사람마다 민감도가 다를 수 있습니다.",
};

async function initSweetenerPage() {
  try {
    const [products, cats, sweets] = await Promise.all([
      fetchJSON("products"),
      fetchJSON("categories"),
      fetchJSON("sweeteners"),
    ]);

    allProducts_sw = products;
    categories_sw = cats;
    sweeteners_sw = sweets;

    const sweetNames = ["알룰로오스", "에리스리톨", "당알코올"];
    initGlobalNav("sweetener", categories_sw, sweetNames);

    let name = getQueryParam("name");
    if (!name) {
      name = "알룰로오스";
    }

    swTitle.textContent = name;
    swDesc.textContent = sweetenerDescriptions[name] || "";

    const filtered = allProducts_sw.filter((p) =>
      (p.sweeteners || []).includes(name)
    );

    if (!filtered.length) {
      swGrid.innerHTML = "";
      swEmpty.classList.remove("hidden");
    } else {
      swEmpty.classList.add("hidden");
      renderProductCards(filtered, swGrid, (p) => {
        window.location.href = `detail.html?id=${p.id}`;
      });
    }
  } catch (err) {
    console.error("대체당 페이지 초기화 실패:", err);
  }
}

window.addEventListener("DOMContentLoaded", initSweetenerPage);
