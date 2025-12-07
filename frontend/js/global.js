const API_BASE = "";
window.API_BASE = API_BASE;

function buildApiUrl(path) {
  if (path.startsWith("http://") || path.startsWith("https://")) {
    return path;
  }
  const clean = path.replace(/^\/+/, "");
  return clean;
}

async function fetchJSON(path) {
  const url = buildApiUrl(path);
  const res = await fetch(url);
  if (!res.ok) {
    console.error("API error:", url, res.status);
    throw new Error("API error");
  }
  return await res.json();
}

function normalizeText(str) {
  if (!str) return "";
  return String(str)
    .toLowerCase()
    .replace(/\s+/g, "")
    .replace(/[^0-9a-z가-힣]/g, "");
}

async function fetchJSON(url) {
  const res = await fetch(url);
  if (!res.ok) {
    console.error("API error:", url, res.status);
    throw new Error("API error");
  }
  return await res.json();
}

function getQueryParam(key) {
  const url = new URL(window.location.href);
  return url.searchParams.get(key);
}

function getSweetenerTagClass(name) {
  if (name === "알룰로오스") return "zse-tag-allulose";
  if (name === "에리스리톨") return "zse-tag-erythritol";
  if (name === "당알코올" || name === "당알콜") return "zse-tag-polyol";
  return "";
}

function renderProductCards(products, container, onClickProduct) {
  container.innerHTML = "";

  products.forEach((p) => {
    const card = document.createElement("article");
    card.className = "zse-product-card";
    card.dataset.id = p.id;

    const thumb = document.createElement("div");
    thumb.className = "zse-card-thumb";

    const img = document.createElement("img");
    img.className = "zse-card-thumb-img";

    if (p.image_url) {
      img.src = p.image_url.startsWith("http") ? p.image_url : p.image_url;
    } else {
      img.src = "assets/no-image.png";
    }

    thumb.appendChild(img);

    const tagRow = document.createElement("div");
    tagRow.className = "zse-tag-row";
    (p.sweeteners || []).forEach((sName) => {
      const tag = document.createElement("span");
      tag.className = "zse-tag " + getSweetenerTagClass(sName);
      tag.textContent = sName;
      tagRow.appendChild(tag);
    });

    const nameEl = document.createElement("div");
    nameEl.className = "zse-card-name";
    nameEl.textContent = p.name;

    card.appendChild(thumb);
    card.appendChild(tagRow);
    card.appendChild(nameEl);

    card.addEventListener("click", () => {
      if (onClickProduct) onClickProduct(p);
    });

    container.appendChild(card);
  });
}

function initGlobalNav(activePage, categories, sweetenerNames) {
  const navProducts = document.getElementById("nav-products");
  const navCategory = document.getElementById("nav-category");
  const navSweetener = document.getElementById("nav-sweetener");
  const categorySubmenu = document.getElementById("category-submenu");
  const sweetenerSubmenu = document.getElementById("sweetener-submenu");

  [navProducts, navCategory, navSweetener].forEach((el) => {
    if (el) el.classList.remove("active");
  });

  if (activePage === "products" && navProducts)
    navProducts.classList.add("active");
  if (activePage === "category" && navCategory)
    navCategory.classList.add("active");
  if (activePage === "sweetener" && navSweetener)
    navSweetener.classList.add("active");

  if (navProducts) {
    navProducts.addEventListener("click", () => {
      window.location.href = "index.html";
    });
  }
  if (navCategory) {
    navCategory.addEventListener("click", () => {
      window.location.href = "category.html";
    });
  }
  if (navSweetener) {
    navSweetener.addEventListener("click", () => {
      window.location.href = "sweetener.html";
    });
  }

  if (categorySubmenu) {
    categorySubmenu.innerHTML = "";
    const categoryNamesOrder = [
      "과자 및 스낵",
      "시럽 및 티베이스",
      "아이스크림",
      "유제품",
      "음료",
      "초콜릿",
      "캔디 및 젤리",
      "탄산",
      "기타",
    ];
    categoryNamesOrder.forEach((name) => {
      const cat = categories.find((c) => c.name === name);
      if (!cat) return;
      const btn = document.createElement("button");
      btn.className = "zse-submenu-item";
      btn.textContent = name;
      btn.addEventListener("click", () => {
        window.location.href = `category.html?category_id=${cat.id}`;
      });
      categorySubmenu.appendChild(btn);
    });
  }

  if (sweetenerSubmenu) {
    sweetenerSubmenu.innerHTML = "";
    sweetenerNames.forEach((name) => {
      const btn = document.createElement("button");
      btn.className = "zse-submenu-item";
      btn.textContent = name;
      btn.addEventListener("click", () => {
        window.location.href = `sweetener.html?name=${encodeURIComponent(
          name
        )}`;
      });
      sweetenerSubmenu.appendChild(btn);
    });
  }

  let catHideTimer = null;
  let sweetHideTimer = null;

  const showCategorySubmenu = () => {
    if (!categorySubmenu) return;
    clearTimeout(catHideTimer);
    if (sweetenerSubmenu) sweetenerSubmenu.classList.remove("visible");
    categorySubmenu.classList.add("visible");
  };
  const hideCategorySubmenu = () => {
    if (!categorySubmenu) return;
    catHideTimer = setTimeout(() => {
      categorySubmenu.classList.remove("visible");
    }, 120);
  };

  const showSweetenerSubmenu = () => {
    if (!sweetenerSubmenu) return;
    clearTimeout(sweetHideTimer);
    if (categorySubmenu) categorySubmenu.classList.remove("visible");
    sweetenerSubmenu.classList.add("visible");
  };
  const hideSweetenerSubmenu = () => {
    if (!sweetenerSubmenu) return;
    sweetHideTimer = setTimeout(() => {
      sweetenerSubmenu.classList.remove("visible");
    }, 120);
  };

  if (navCategory && categorySubmenu) {
    navCategory.addEventListener("mouseenter", showCategorySubmenu);
    navCategory.addEventListener("mouseleave", hideCategorySubmenu);
    categorySubmenu.addEventListener("mouseenter", () => {
      clearTimeout(catHideTimer);
    });
    categorySubmenu.addEventListener("mouseleave", hideCategorySubmenu);
  }

  if (navSweetener && sweetenerSubmenu) {
    navSweetener.addEventListener("mouseenter", showSweetenerSubmenu);
    navSweetener.addEventListener("mouseleave", hideSweetenerSubmenu);
    sweetenerSubmenu.addEventListener("mouseenter", () => {
      clearTimeout(sweetHideTimer);
    });
    sweetenerSubmenu.addEventListener("mouseleave", hideSweetenerSubmenu);
  }
}
