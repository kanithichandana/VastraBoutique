/* Vastra storefront: open and close the cart drawer. */
(() => {
  "use strict";

  const drawer = document.getElementById("cart-drawer");
  const scrim = document.getElementById("cart-scrim");
  if (!drawer || !scrim) return;

  function openCart() {
    drawer.hidden = false;
    scrim.hidden = false;
    const closeButton = drawer.querySelector("[data-close-cart]");
    if (closeButton) closeButton.focus();
  }

  function closeCart() {
    drawer.hidden = true;
    scrim.hidden = true;
  }

  document.querySelectorAll("[data-open-cart]").forEach((button) => {
    button.addEventListener("click", openCart);
  });

  document.querySelectorAll("[data-close-cart]").forEach((button) => {
    button.addEventListener("click", closeCart);
  });

  scrim.addEventListener("click", closeCart);

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && !drawer.hidden) closeCart();
  });
})();
