let allProducts_cat = [];
let categories_cat = [];
let sweeteners_cat = [];

const catTitle = document.getElementById("category-title");
const catDesc = document.getElementById("category-desc");
const catGrid = document.getElementById("product-grid");
const catEmpty = document.getElementById("empty-message");

async function initCategoryPage() {
  try {
    const [products, cats, sweets] = await Promise.all([
      fetchJSON("products"),
      fetchJSON("categories"),
      fetchJSON("sweeteners"),
    ]);

    allProducts_cat = products;
    categories_cat = cats;
    sweeteners_cat = sweets;

    const sweetNames = ["알룰로오스", "에리스리톨", "당알코올"];
    initGlobalNav("category", categories_cat, sweetNames);

    let categoryId = getQueryParam("category_id");
    if (!categoryId && categories_cat.length > 0) {
      categoryId = categories_cat[0].id;
    }
    categoryId = Number(categoryId);

    const cat = categories_cat.find((c) => c.id === categoryId);
    if (cat) {
      catTitle.textContent = cat.name;
    } else {
      catTitle.textContent = "카테고리 선택";
      catDesc.textContent = "상단 카테고리 메뉴에서 카테고리를 선택해 주세요.";
      catGrid.innerHTML = "";
      return;
    }

    const filtered = allProducts_cat.filter(
      (p) => p.category_id === categoryId
    );

    if (!filtered.length) {
      catGrid.innerHTML = "";
      catEmpty.classList.remove("hidden");
    } else {
      catEmpty.classList.add("hidden");
      renderProductCards(filtered, catGrid, (p) => {
        window.location.href = `detail.html?id=${p.id}`;
      });
    }
  } catch (err) {
    console.error("카테고리 페이지 초기화 실패:", err);
  }
}

window.addEventListener("DOMContentLoaded", initCategoryPage);
