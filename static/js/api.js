function escapeHtml(value) {
  return String(value === null || value === undefined ? "" : value).replace(/[&<>"']/g, (ch) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  }[ch]));
}

function getImageUrl(image) {
  if (!image) {
    return '/static/images/placeholder.png';
  }
  if (image.startsWith('http://') || image.startsWith('https://')) {
    return image;
  }
  if (image.startsWith('/static')) {
    return image;
  }
  return `https://hfuajgmfmqwzjjzkdluo.supabase.co/storage/v1/object/public/med-images/${image}`;
}

const API = {

  getCsrfToken() {
    const match = document.cookie.match(/(?:^|;\s*)csrf_token=([^;]+)/);
    return match ? match[1] : null;
  },

  async request(method, path, body = null, formData = false, extraHeaders = {}) {
    const options = {
      method,
      headers: {},
    };
    Object.assign(options.headers, extraHeaders);

    if (method !== "GET" && method !== "HEAD") {
      const csrfToken = this.getCsrfToken();
      if (csrfToken) {
        options.headers["X-CSRF-Token"] = csrfToken;
      }
    }

    if (body) {
      if (formData) {
        options.body = body;
      } else {
        options.headers["Content-Type"] = "application/json";
        options.body = JSON.stringify(body);
      }
    }

    const response = await fetch(`/api${path}`, options);
    const data = await response.json();
    return { ok: response.ok, status: response.status, data };
  },

  getProducts() {
    return this.request("GET", "/products");
  },

  getProduct(id) {
    return this.request("GET", `/products/${id}`);
  },

  addProduct(formData) {
    return this.request("POST", "/products", formData, true);
  },

  editProduct(id, formData) {
    return this.request("PUT", `/products/${id}`, formData, true);
  },

  deleteProduct(id) {
    return this.request("DELETE", `/products/${id}`);
  },

  deleteProductImage(id, imageId) {
    return this.request("DELETE", `/products/${id}/images/${imageId}`);
  },

  getOrders() {
    return this.request("GET", "/orders");
  },

  createOrder(items, checkoutData, idempotencyKey) {
    return this.request("POST", "/orders", { items, ...checkoutData }, false, { "Idempotency-Key": idempotencyKey });
  },

  getPage(slug) {
    return this.request("GET", `/pages/${slug}`);
  },

  updatePage(slug, title, body) {
    return this.request("PUT", `/pages/${slug}`, { title, body });
  },

  login(username, password) {
    return this.request("POST", "/login", { username, password });
  },

  register(username, email, password) {
    return this.request("POST", "/register", { username, email, password });
  },

  logout() {
    return this.request("POST", "/logout");
  },

  checkSession() {
    return this.request("GET", "/session");
  },
};