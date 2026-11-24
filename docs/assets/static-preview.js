/* Vastra static preview: categories, search, accounts and cart in the browser. */
(() => {
  "use strict";

  const dataNode = document.getElementById("vastra-static-data");
  if (!dataNode) return;

  let DATA;
  try {
    DATA = JSON.parse(dataNode.textContent);
  } catch (error) {
    console.error("Vastra preview data could not be read", error);
    return;
  }

  const products = DATA.products || [];
  const categories = DATA.categories || [];
  const productByCode = new Map(products.map((product) => [product.code, product]));

  const KEYS = {
    accounts: "vastra_static_accounts",
    session: "vastra_static_session",
    cart: "vastra_static_cart_",
  };

  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => Array.from(root.querySelectorAll(selector));

  function readValue(key, fallback) {
    try {
      const raw = localStorage.getItem(key);
      return raw === null ? fallback : JSON.parse(raw);
    } catch (error) {
      return fallback;
    }
  }

  function writeValue(key, value) {
    try {
      localStorage.setItem(key, JSON.stringify(value));
      return true;
    } catch (error) {
      console.error("Vastra preview could not save browser data", error);
      toast("Browser storage is blocked. Allow site data and try again.");
      return false;
    }
  }

  function escapeHtml(value) {
    return String(value === undefined || value === null ? "" : value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function toHex(bytes) {
    return Array.from(bytes)
      .map((byte) => byte.toString(16).padStart(2, "0"))
      .join("");
  }

  function newSalt() {
    if (globalThis.crypto && crypto.getRandomValues) {
      const bytes = new Uint8Array(16);
      crypto.getRandomValues(bytes);
      return toHex(bytes);
    }
    // Fallback for non-secure contexts such as opening the HTML from disk.
    return `${Date.now().toString(16)}-${Math.random().toString(16).slice(2)}`;
  }

  async function hashPassword(password, salt) {
    const input = `${salt}:${password}`;
    if (globalThis.crypto && crypto.subtle && crypto.subtle.digest) {
      const bytes = new TextEncoder().encode(input);
      const digest = await crypto.subtle.digest("SHA-256", bytes);
      return toHex(new Uint8Array(digest));
    }
    // Fallback keeps the preview usable outside HTTPS; accounts stay local only.
    let hash = 0;
    for (let index = 0; index < input.length; index += 1) {
      hash = (hash * 31 + input.charCodeAt(index)) | 0;
    }
    return `fallback-${(hash >>> 0).toString(16)}-${input.length}`;
  }

  function getAccounts() {
    const accounts = readValue(KEYS.accounts, []);
    return Array.isArray(accounts) ? accounts : [];
  }

  function currentUsername() {
    const username = readValue(KEYS.session, null);
    if (!username) return null;
    const found = getAccounts().some(
      (account) => account.username.toLowerCase() === String(username).toLowerCase()
    );
    return found ? username : null;
  }

  function cartKey(username) {
    return KEYS.cart + username.toLowerCase();
  }

  function getCart() {
    const username = currentUsername();
    if (!username) return {};
    const cart = readValue(cartKey(username), {});
    return cart && typeof cart === "object" && !Array.isArray(cart) ? cart : {};
  }

  function saveCart(cart) {
    const username = currentUsername();
    if (username) writeValue(cartKey(username), cart);
  }

  function cartLines() {
    return Object.entries(getCart())
      .filter(([code, quantity]) => productByCode.has(code) && Number(quantity) > 0)
      .map(([code, quantity]) => ({
        product: productByCode.get(code),
        quantity: Number(quantity),
      }));
  }

  function cartCount() {
    return cartLines().reduce((total, line) => total + line.quantity, 0);
  }

  function cartTotal() {
    return cartLines().reduce(
      (total, line) => total + Number(line.product.price) * line.quantity,
      0
    );
  }

  function money(value) {
    return `₹${Number(value).toFixed(2)}`;
  }

  const state = { category: "", query: "" };

  function readUrl() {
    const params = new URLSearchParams(window.location.search);
    state.category = params.get("category") || "";
    state.query = (params.get("q") || "").trim();
    if (state.category && !categories.some((item) => item.value === state.category)) {
      state.category = "";
    }
    const input = $("#store-search");
    if (input) input.value = state.query;
  }

  function syncUrl() {
    const params = new URLSearchParams();
    if (state.category) params.set("category", state.category);
    if (state.query) params.set("q", state.query);
    const search = params.toString();
    const hash = window.location.hash || "#products";
    history.replaceState(
      null,
      "",
      window.location.pathname + (search ? `?${search}` : "") + hash
    );
  }

  function productCard(product) {
    const meta = [product.color, product.size, product.fabric]
      .filter(Boolean)
      .map(escapeHtml)
      .join(" · ");
    const image = product.image
      ? `<img src="${escapeHtml(product.image)}" alt="${escapeHtml(product.name)}">`
      : `<span class="product-monogram">${escapeHtml(
          String(product.categoryLabel || "").slice(0, 1)
        )}</span>`;
    const action = product.available
      ? `<button type="button" class="add-cart" data-add-to-cart="${escapeHtml(
          product.code
        )}">Add to cart</button>`
      : `<span class="unavailable">Unavailable</span>`;

    return `<article class="product-card">
  <div class="product-image">
    ${image}
    <span class="product-code">${escapeHtml(product.code)}</span>
  </div>
  <div class="product-body">
    <p class="product-category">${escapeHtml(product.categoryLabel)}</p>
    <h3>${escapeHtml(product.name)}</h3>
    <p class="product-meta">${meta}</p>
    <div class="product-footer">
      <strong class="product-price">${money(product.price)}</strong>
      ${action}
    </div>
  </div>
</article>`;
  }

  function matchedCategories(query) {
    if (query.length < 2) return [];
    const needle = query.toLowerCase();
    return categories
      .filter((item) =>
        [item.value, item.label].some((text) =>
          String(text || "").toLowerCase().includes(needle)
        )
      )
      .map((item) => item.value);
  }

  function matchesQuery(product, query) {
    if (!query) return true;
    const needle = query.toLowerCase();
    const fields = [
      product.name,
      product.code,
      product.category,
      product.categoryLabel,
      product.color,
      product.fabric,
      product.size,
      product.description,
    ];
    return fields.some((field) =>
      String(field || "").toLowerCase().includes(needle)
    );
  }

  function filteredProducts() {
    return products.filter(
      (product) =>
        (!state.category || product.category === state.category) &&
        matchesQuery(product, state.query)
    );
  }

  function renderProducts() {
    const container = $("#static-product-results");
    if (!container) return;

    const matches = filteredProducts();
    const groupedValues = matchedCategories(state.query);
    const heading = $("#products .section-intro h2");
    if (heading) {
      if (state.query) {
        heading.textContent = `Results for “${state.query}”`;
      } else {
        const active = categories.find((item) => item.value === state.category);
        heading.textContent = active ? `Products · ${active.label}` : "Products";
      }
    }

    const clear = $("[data-clear-search]");
    if (clear) clear.hidden = !state.query;

    $$(".category-arch").forEach((arch) => {
      arch.classList.toggle("active", arch.dataset.category === state.category);
    });

    const noResults =
      '<p class="empty-products">No products match your search. Try another term or clear the search.</p>';

    if (groupedValues.length) {
      container.className = "static-category-groups";
      const groups = categories
        .filter((item) => groupedValues.includes(item.value))
        .map((item) => ({
          label: item.label,
          items: matches.filter((product) => product.category === item.value),
        }))
        .filter((group) => group.items.length);

      container.innerHTML = groups.length
        ? groups
            .map(
              (group) => `<div class="category-group">
  <div class="category-group-heading">
    <h3>${escapeHtml(group.label)}</h3>
    <span>${group.items.length} item${group.items.length === 1 ? "" : "s"}</span>
  </div>
  <div class="product-grid">${group.items.map(productCard).join("")}</div>
</div>`
            )
            .join("")
        : noResults;
      return;
    }

    container.className = "product-grid";
    container.innerHTML = matches.length
      ? matches.map(productCard).join("")
      : noResults;
  }

  function renderHeader() {
    const username = currentUsername();
    const login = $("[data-header-login]");
    const signup = $("[data-header-signup]");
    const chip = $("[data-account-chip]");
    const logout = $("[data-logout]");

    if (login) login.hidden = Boolean(username);
    if (signup) signup.hidden = Boolean(username);
    if (chip) {
      chip.hidden = !username;
      chip.textContent = username ? `Hi, ${username}` : "";
    }
    if (logout) logout.hidden = !username;
  }

  function renderCart() {
    const count = $("[data-cart-count]");
    const total = $("[data-cart-total]");
    const body = $("[data-cart-body]");
    const cta = $("[data-cart-cta]");
    const lines = cartLines();

    if (count) count.textContent = String(cartCount());
    if (total) total.textContent = money(cartTotal());

    if (body) {
      body.innerHTML = lines.length
        ? lines
            .map(
              (line) => `<div class="cart-line">
  <div>
    <strong>${escapeHtml(line.product.name)}</strong>
    <small>${escapeHtml(line.product.code)} · Qty ${line.quantity}</small>
  </div>
  <span>${money(Number(line.product.price) * line.quantity)}</span>
  <button type="button" class="cart-remove" data-remove-from-cart="${escapeHtml(
    line.product.code
  )}" aria-label="Remove ${escapeHtml(line.product.name)}">×</button>
</div>`
            )
            .join("")
        : `<p class="cart-empty">${
            currentUsername()
              ? "Your cart is empty. Add a piece you love."
              : "Sign in to start your cart."
          }</p>`;
    }

    if (cta) {
      if (currentUsername()) {
        cta.textContent = "Buy now";
        cta.dataset.closeCart = "";
        delete cta.dataset.openLogin;
      } else {
        cta.textContent = "Sign in to add items";
        cta.dataset.openLogin = "";
        delete cta.dataset.closeCart;
      }
    }

    renderHeader();
  }

  function openModal(id) {
    closeModals();
    const modal = document.getElementById(id);
    if (!modal) return;
    modal.hidden = false;
    const firstInput = $("input", modal);
    if (firstInput) firstInput.focus();
  }

  function closeModals() {
    $$(".va-modal").forEach((modal) => {
      modal.hidden = true;
    });
  }

  function showError(form, message) {
    const error = $("[data-error]", form);
    if (!error) return;
    error.textContent = message;
    error.hidden = false;
  }

  function clearError(form) {
    const error = $("[data-error]", form);
    if (!error) return;
    error.textContent = "";
    error.hidden = true;
  }

  let toastTimer;
  function toast(message) {
    const element = $("#va-toast");
    if (!element) return;
    element.textContent = message;
    element.hidden = false;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => {
      element.hidden = true;
    }, 2600);
  }

  function closeCart() {
    const drawer = $("#cart-drawer");
    const scrim = $("#cart-scrim");
    if (drawer) drawer.hidden = true;
    if (scrim) scrim.hidden = true;
  }

  function scrollToProducts() {
    const productsSection = $("#products");
    if (productsSection) {
      productsSection.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }

  // Search ---------------------------------------------------------------
  const searchForm = $("[data-static-search]");
  if (searchForm) {
    searchForm.addEventListener("submit", (event) => {
      event.preventDefault();
      const input = $("#store-search");
      state.query = ((input && input.value) || "").trim();
      syncUrl();
      renderProducts();
      scrollToProducts();
    });
  }

  // Sign up --------------------------------------------------------------
  const signupForm = $("#signup-form");
  if (signupForm) {
    signupForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      clearError(signupForm);
      const form = event.currentTarget;
      const username = form.elements.username.value.trim().toLowerCase();
      const phone = form.elements.phone.value.trim();
      const address = form.elements.address.value.trim();
      const password = form.elements.password.value;

      if (!username || !phone || !address || !password) {
        showError(form, "Please complete every field.");
        return;
      }
      if (password.length < 8) {
        showError(form, "Use at least 8 characters for your password.");
        return;
      }
      const accounts = getAccounts();
      if (accounts.some((account) => account.username.toLowerCase() === username)) {
        showError(form, "That username is already taken.");
        return;
      }
      if (accounts.some((account) => account.phone === phone)) {
        showError(form, "An account with that phone number already exists.");
        return;
      }

      const salt = newSalt();
      const hash = await hashPassword(password, salt);
      const nextAccounts = accounts.concat([
        { username, phone, address, salt, hash },
      ]);
      if (!writeValue(KEYS.accounts, nextAccounts)) {
        showError(form, "Browser storage is blocked. Allow site data and try again.");
        return;
      }

      form.reset();
      closeModals();
      const loginForm = $("#login-form");
      if (loginForm) loginForm.elements.username.value = username;
      openModal("login-modal");
      toast("Account created. Sign in to continue.");
    });
  }

  // Sign in --------------------------------------------------------------
  const loginForm = $("#login-form");
  if (loginForm) {
    loginForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      clearError(loginForm);
      const form = event.currentTarget;
      const username = form.elements.username.value.trim().toLowerCase();
      const password = form.elements.password.value;

      if (!username || !password) {
        showError(form, "Enter your username and password.");
        return;
      }

      const account = getAccounts().find(
        (item) => item.username.toLowerCase() === username
      );
      if (!account) {
        showError(form, "No account found with that username.");
        return;
      }

      const hash = await hashPassword(password, account.salt);
      if (hash !== account.hash) {
        showError(form, "Incorrect password.");
        return;
      }

      if (!writeValue(KEYS.session, account.username)) {
        showError(form, "Browser storage is blocked. Allow site data and try again.");
        return;
      }
      form.reset();
      closeModals();
      renderCart();
      toast(`Welcome back, ${account.username}.`);
    });
  }

  // Click delegation -----------------------------------------------------
  document.addEventListener("click", (event) => {
    const target = event.target;

    const arch = target.closest("[data-category]");
    if (arch) {
      event.preventDefault();
      state.category = state.category === arch.dataset.category ? "" : arch.dataset.category;
      syncUrl();
      renderProducts();
      scrollToProducts();
      return;
    }

    if (target.closest("[data-clear-search]")) {
      event.preventDefault();
      state.query = "";
      const input = $("#store-search");
      if (input) input.value = "";
      syncUrl();
      renderProducts();
      return;
    }

    if (target.closest("[data-open-login]")) {
      event.preventDefault();
      openModal("login-modal");
      return;
    }

    if (target.closest("[data-open-signup]")) {
      event.preventDefault();
      openModal("signup-modal");
      return;
    }

    if (target.closest("[data-logout]")) {
      writeValue(KEYS.session, null);
      renderCart();
      toast("Signed out.");
      return;
    }

    if (target.closest("[data-close-modal]")) {
      closeModals();
      return;
    }

    if (target.closest("[data-close-cart]")) {
      closeCart();
      return;
    }

    const addButton = target.closest("[data-add-to-cart]");
    if (addButton) {
      if (!currentUsername()) {
        openModal("login-modal");
        return;
      }
      const code = addButton.dataset.addToCart;
      const product = productByCode.get(code);
      if (!product) return;
      const cart = getCart();
      const next = (Number(cart[code]) || 0) + 1;
      const stock = Number(product.stock) || 0;
      if (stock && next > stock) {
        toast(`Only ${stock} available.`);
        return;
      }
      cart[code] = next;
      saveCart(cart);
      renderCart();
      toast(`${product.name} added to cart.`);
      return;
    }

    const removeButton = target.closest("[data-remove-from-cart]");
    if (removeButton) {
      const cart = getCart();
      delete cart[removeButton.dataset.removeFromCart];
      saveCart(cart);
      renderCart();
    }
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") closeModals();
  });

  // Start ----------------------------------------------------------------
  readUrl();
  renderProducts();
  renderCart();
})();
