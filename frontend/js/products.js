let allProducts = [];
let categories = [];
let sweeteners = [];

const searchSection = document.getElementById("search-section");
const searchInput = document.getElementById("search-input");
const searchClear = document.getElementById("search-clear");
const uploadButton = document.getElementById("upload-button");

const productGrid = document.getElementById("product-grid");
const emptyMessage = document.getElementById("empty-message");

const uploadModalOverlay = document.getElementById("upload-modal-overlay");
const uploadModalClose = document.getElementById("upload-modal-close");
const uploadCancelBtn = document.getElementById("upload-cancel-btn");
const uploadConfirmBtn = document.getElementById("upload-confirm-btn");
const uploadCategorySelect = document.getElementById("upload-category-select");
const uploadFileInput = document.getElementById("upload-file-input");

const predictModalOverlay = document.getElementById("predict-modal-overlay");
const predictModalClose = document.getElementById("predict-modal-close");
const predictResults = document.getElementById("predict-results");

async function initProductsPage() {
  try {
    const [products, cats, sweets] = await Promise.all([
      fetchJSON(`${API_BASE}/products`),
      fetchJSON(`${API_BASE}/categories`),
      fetchJSON(`${API_BASE}/sweeteners`),
    ]);

    allProducts = products;
    categories = cats;
    sweeteners = sweets;

    const sweetNames = ["알룰로오스", "에리스리톨", "당알코올"];
    initGlobalNav("products", categories, sweetNames);

    initUploadCategoryOptions();
    initSearch();
    renderProductList(allProducts);
  } catch (err) {
    console.error("제품 페이지 초기화 실패:", err);
  }
}

function initUploadCategoryOptions() {
  uploadCategorySelect.innerHTML = "<option value=''>선택해주세요</option>";
  categories.forEach((cat) => {
    const opt = document.createElement("option");
    opt.value = cat.id;
    opt.textContent = cat.name;
    uploadCategorySelect.appendChild(opt);
  });
}

function initSearch() {
  searchInput.addEventListener("input", () => {
    const text = searchInput.value.trim();
    const box = searchInput.parentElement;

    if (text.length > 0) box.classList.add("has-text");
    else box.classList.remove("has-text");

    const query = normalizeText(text);
    const filtered = query
      ? allProducts.filter((p) => normalizeText(p.name).includes(query))
      : allProducts;

    renderProductList(filtered);
  });

  searchClear.addEventListener("click", () => {
    searchInput.value = "";
    searchInput.dispatchEvent(new Event("input"));
    searchInput.focus();
  });

  uploadButton.addEventListener("click", () => {
    uploadModalOverlay.classList.remove("hidden");
  });

  const closeUploadModal = () => {
    uploadModalOverlay.classList.add("hidden");
    uploadFileInput.value = "";
    uploadCategorySelect.value = "";
  };

  uploadModalClose.addEventListener("click", closeUploadModal);
  uploadCancelBtn.addEventListener("click", closeUploadModal);

  uploadConfirmBtn.addEventListener("click", async () => {
    const categoryId = uploadCategorySelect.value;
    const files = uploadFileInput.files;

    if (!categoryId) {
      alert("카테고리를 선택해주세요.");
      return;
    }
    if (!files || files.length === 0) {
      alert("이미지 파일을 선택해주세요.");
      return;
    }

    const file = files[0];
    const formData = new FormData();
    formData.append("category_id", categoryId);
    formData.append("file", file);

    uploadConfirmBtn.disabled = true;
    const originalText = uploadConfirmBtn.textContent;
    uploadConfirmBtn.textContent = "분석 중...";

    try {
      const res = await fetch(`${API_BASE}/predict`, {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        const text = await res.text();
        throw new Error(text || "예측 요청 실패");
      }

      const data = await res.json();
      const results = data.results || [];

      if (!results.length) {
        alert("예측 결과를 찾지 못했습니다.");
        return;
      }

      closeUploadModal();
      openPredictModal(results);
    } catch (err) {
      console.error(err);
      alert("이미지 분석 중 오류가 발생했습니다.");
    } finally {
      uploadConfirmBtn.disabled = false;
      uploadConfirmBtn.textContent = originalText;
    }
  });

  document.addEventListener("keydown", (e) => {
    if (
      e.key === "Escape" &&
      !uploadModalOverlay.classList.contains("hidden")
    ) {
      uploadModalOverlay.classList.add("hidden");
    }
  });

  if (predictModalClose) {
    predictModalClose.addEventListener("click", closePredictModal);
  }
}

function openPredictModal(results) {
  if (!predictModalOverlay || !predictResults) return;

  predictResults.innerHTML = "";

  results.forEach((item) => {
    const card = document.createElement("div");
    card.className = "zse-predict-card";
    if (item.rank === 1) {
      card.classList.add("top");
    }

    const thumbWrap = document.createElement("div");
    thumbWrap.className = "zse-predict-thumb";

    const img = document.createElement("img");
    let imgSrc = "assets/no-image.png";

    if (item.product_id) {
      const p = allProducts.find((x) => x.id === item.product_id);
      if (p && p.image_url) {
        const base = window.API_BASE || "http://127.0.0.1:8000";
        imgSrc = p.image_url.startsWith("http")
          ? p.image_url
          : `${base}${p.image_url}`;
      }
    }
    img.src = imgSrc;
    img.alt = item.name || "예측 제품";

    thumbWrap.appendChild(img);

    const info = document.createElement("div");
    info.className = "zse-predict-info";

    const nameEl = document.createElement("div");
    nameEl.className = "zse-predict-name";
    nameEl.textContent = `${item.rank}. ${item.name}`;

    const subEl = document.createElement("div");
    subEl.className = "zse-predict-sub";
    subEl.textContent = item.product_id
      ? "클릭하면 상세 정보를 확인할 수 있습니다."
      : "DB에 등록되지 않은 제품일 수 있습니다.";

    info.appendChild(nameEl);
    info.appendChild(subEl);

    card.appendChild(thumbWrap);
    card.appendChild(info);

    card.addEventListener("click", () => {
      if (item.product_id) {
        window.location.href = `detail.html?id=${item.product_id}`;
      }
    });

    predictResults.appendChild(card);
  });

  predictModalOverlay.classList.remove("hidden");
}

function closePredictModal() {
  if (!predictModalOverlay) return;
  predictModalOverlay.classList.add("hidden");
}

function renderProductList(list) {
  if (!list || list.length === 0) {
    productGrid.innerHTML = "";
    emptyMessage.classList.remove("hidden");
    return;
  }
  emptyMessage.classList.add("hidden");

  renderProductCards(list, productGrid, (p) => {
    window.location.href = `detail.html?id=${p.id}`;
  });
}

window.addEventListener("DOMContentLoaded", initProductsPage);
