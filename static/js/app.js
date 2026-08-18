const grid = document.getElementById("productsGrid");
const template = document.getElementById("productCardTemplate");
const refreshBtn = document.getElementById("refreshBtn");

const FALLBACK_IMAGE =
  "https://images.unsplash.com/photo-1542838132-92c53300491e?auto=format&fit=crop&w=1200&q=80";

function formatPrice(price) {
  return new Intl.NumberFormat("ru-RU", {
    style: "currency",
    currency: "RUB",
    maximumFractionDigits: 0,
  }).format(price);
}

function renderProducts(products) {
  grid.innerHTML = "";

  if (!products.length) {
    grid.innerHTML = '<p class="empty">Пока нет товаров. Добавь первый товар через бота.</p>';
    return;
  }

  products.forEach((product, index) => {
    const node = template.content.cloneNode(true);

    const image = node.querySelector(".card-image");
    image.src = product.image_url || FALLBACK_IMAGE;
    image.alt = product.title;

    node.querySelector(".chip").textContent = product.category || "Без категории";
    node.querySelector(".card-title").textContent = product.title;
    node.querySelector(".card-text").textContent = product.description || "Описание не указано.";
    node.querySelector(".price").textContent = formatPrice(product.price);
    node.querySelector(".stock").textContent = `В наличии: ${product.stock}`;

    const card = node.querySelector(".card");
    card.style.animationDelay = `${index * 45}ms`;

    grid.appendChild(node);
  });
}

async function loadProducts() {
  try {
    const response = await fetch("/api/products");
    if (!response.ok) {
      throw new Error("Не удалось загрузить каталог");
    }

    const products = await response.json();
    renderProducts(products);
  } catch (error) {
    grid.innerHTML = `<p class="empty">${error.message}</p>`;
  }
}

refreshBtn.addEventListener("click", loadProducts);
loadProducts();

// Опционально: тихо обновляем список каждые 30 секунд.
setInterval(loadProducts, 30000);
