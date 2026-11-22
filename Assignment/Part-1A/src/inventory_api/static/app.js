"use strict";

const API_URL = "/items";

const elements = {
    totalItems: document.getElementById("totalItems"),
    totalQuantity: document.getElementById("totalQuantity"),
    inventoryValue: document.getElementById("inventoryValue"),
    lowStockCount: document.getElementById("lowStockCount"),
    tableBody: document.getElementById("inventoryTableBody"),
    resultCount: document.getElementById("resultCount"),
    lowStockList: document.getElementById("lowStockList"),
    searchInput: document.getElementById("searchInput"),
    categoryFilter: document.getElementById("categoryFilter"),
    sortFilter: document.getElementById("sortFilter"),
    messageArea: document.getElementById("messageArea"),
    modal: document.getElementById("itemModal"),
    form: document.getElementById("itemForm"),
    modalTitle: document.getElementById("modalTitle"),
    itemId: document.getElementById("itemId"),
    itemIdField: document.getElementById("itemIdField"),
    itemName: document.getElementById("itemName"),
    itemCategory: document.getElementById("itemCategory"),
    itemQuantity: document.getElementById("itemQuantity"),
    itemPrice: document.getElementById("itemPrice"),
    itemExpiry: document.getElementById("itemExpiry"),
    saveButton: document.getElementById("saveButton")
};

let inventory = [];
let lowStockItems = [];
let editingItemId = null;

async function apiRequest(url, options = {}) {
    const response = await fetch(url, {
        ...options,
        headers: {
            "Content-Type": "application/json",
            ...options.headers
        }
    });

    if (!response.ok) {
        let message = `Request failed (${response.status})`;

        try {
            const error = await response.json();
            message = error.detail || message;
        } catch {
            // Keep the fallback message.
        }

        throw new Error(message);
    }

    if (response.status === 204) {
        return null;
    }

    return response.json();
}

function showMessage(message, type = "success") {
    elements.messageArea.textContent = message;
    elements.messageArea.className =
        `message-area message-${type}`;
}

function clearMessage() {
    elements.messageArea.textContent = "";
    elements.messageArea.className = "message-area";
}

function formatNumber(value) {
    return new Intl.NumberFormat("en-IN", {
        maximumFractionDigits: 2
    }).format(Number(value) || 0);
}

function formatCurrency(value, currency = "INR") {
    try {
        return new Intl.NumberFormat("en-IN", {
            style: "currency",
            currency
        }).format(Number(value) || 0);
    } catch {
        return `₹${formatNumber(value)}`;
    }
}

function formatDate(value) {
    if (!value) return "—";

    const date = new Date(`${value}T00:00:00`);

    if (Number.isNaN(date.getTime())) return value;

    return date.toLocaleDateString("en-IN", {
        day: "2-digit",
        month: "short",
        year: "numeric"
    });
}

function getStockStatus(item) {
    if (Number(item.quantity) === 0) {
        return { label: "Out of Stock", className: "stock-empty" };
    }

    if (lowStockItems.some(lowItem => lowItem.id === item.id)) {
        return { label: "Low Stock", className: "stock-low" };
    }

    return { label: "In Stock", className: "stock-good" };
}

function createCell(text, className = "") {
    const cell = document.createElement("td");
    cell.textContent = text;

    if (className) cell.className = className;

    return cell;
}

function createActionButton(label, className, callback) {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = label;
    button.className = `action-button ${className}`;

    button.addEventListener("click", callback);

    return button;
}

function renderInventory(items) {
    elements.tableBody.replaceChildren();

    if (items.length === 0) {
        const row = document.createElement("tr");
        const cell = createCell(
            "No inventory items found. Add your first item to get started."
        );
        cell.colSpan = 7;
        cell.className = "empty-state";
        row.appendChild(cell);
        elements.tableBody.appendChild(row);
    }

    items.forEach(item => {
        const row = document.createElement("tr");

        const itemCell = document.createElement("td");
        const name = document.createElement("span");
        name.textContent = item.name;
        name.className = "item-name";

        const id = document.createElement("span");
        id.textContent = item.id;
        id.className = "item-id";

        itemCell.append(name, id);

        const category = document.createElement("td");
        const categoryBadge = document.createElement("span");
        categoryBadge.className = "category-badge";
        categoryBadge.textContent = item.category;
        category.appendChild(categoryBadge);

        const status = getStockStatus(item);
        const statusCell = document.createElement("td");
        const statusBadge = document.createElement("span");
        statusBadge.className = `stock-badge ${status.className}`;
        statusBadge.textContent = status.label;
        statusCell.appendChild(statusBadge);

        const actions = document.createElement("td");
        actions.append(
            createActionButton("Edit", "", () => openEditModal(item)),
            createActionButton("Delete", "delete", () => deleteItem(item.id))
        );

        row.append(
            itemCell,
            category,
            createCell(formatNumber(item.quantity)),
            createCell(formatCurrency(
                item.unit_price,
                item.currency
            )),
            createCell(formatDate(item.expiry_date)),
            statusCell,
            actions
        );

        elements.tableBody.appendChild(row);
    });

    elements.resultCount.textContent =
        `Showing ${items.length} of ${inventory.length} items`;
}

function renderDashboard() {
    const totalItems = inventory.length;

    const totalQuantity = inventory.reduce(
        (sum, item) => sum + Number(item.quantity),
        0
    );

    const totalValue = inventory.reduce(
        (sum, item) =>
            sum + Number(item.quantity) * Number(item.unit_price),
        0
    );

    const currency = inventory[0]?.currency || "INR";

    elements.totalItems.textContent = formatNumber(totalItems);
    elements.totalQuantity.textContent = formatNumber(totalQuantity);
    elements.inventoryValue.textContent =
        formatCurrency(totalValue, currency);
    elements.lowStockCount.textContent =
        formatNumber(lowStockItems.length);
}

function renderLowStock() {
    elements.lowStockList.replaceChildren();

    if (lowStockItems.length === 0) {
        const message = document.createElement("p");
        message.className = "muted";
        message.textContent = "No low-stock items. Everything looks good!";
        elements.lowStockList.appendChild(message);
        return;
    }

    lowStockItems.forEach(item => {
        const card = document.createElement("article");
        card.className = "low-stock-card";

        const name = document.createElement("strong");
        name.textContent = item.name;

        const details = document.createElement("span");
        details.textContent =
            `${item.category} · ${formatNumber(item.quantity)} units remaining`;

        card.append(name, details);
        elements.lowStockList.appendChild(card);
    });
}

function populateCategories() {
    const selectedCategory = elements.categoryFilter.value;

    const categories = [...new Set(
        inventory.map(item => item.category)
    )].sort((a, b) => a.localeCompare(b));

    elements.categoryFilter.replaceChildren();

    const allOption = document.createElement("option");
    allOption.value = "";
    allOption.textContent = "All categories";
    elements.categoryFilter.appendChild(allOption);

    categories.forEach(category => {
        const option = document.createElement("option");
        option.value = category;
        option.textContent = category;
        elements.categoryFilter.appendChild(option);
    });

    if (categories.includes(selectedCategory)) {
        elements.categoryFilter.value = selectedCategory;
    }
}

function applyFilters() {
    const search = elements.searchInput.value.trim().toLowerCase();
    const category = elements.categoryFilter.value;

    let filtered = inventory.filter(item => {
        const matchesSearch =
            item.name.toLowerCase().includes(search) ||
            item.id.toLowerCase().includes(search);

        const matchesCategory =
            !category || item.category === category;

        return matchesSearch && matchesCategory;
    });

    const sortBy = elements.sortFilter.value;

    if (sortBy) {
        filtered = [...filtered].sort((a, b) => {
            if (sortBy === "expiry_date") {
                if (!a.expiry_date) return 1;
                if (!b.expiry_date) return -1;

                return a.expiry_date.localeCompare(b.expiry_date);
            }

            return Number(a[sortBy]) - Number(b[sortBy]);
        });
    }

    renderInventory(filtered);
}

async function loadInventory() {
    elements.tableBody.innerHTML =
        '<tr><td colspan="7" class="empty-state">Loading inventory...</td></tr>';

    try {
        const [items, lowItems] = await Promise.all([
            apiRequest(API_URL),
            apiRequest(`${API_URL}/low-stock`)
        ]);

        inventory = items;
        lowStockItems = lowItems;

        populateCategories();
        renderDashboard();
        renderLowStock();
        applyFilters();
        clearMessage();
    } catch (error) {
        showMessage(error.message, "error");
        elements.tableBody.replaceChildren();

        const row = document.createElement("tr");
        const cell = createCell(
            "Could not load inventory. Check that the API server is running."
        );
        cell.colSpan = 7;
        cell.className = "empty-state";
        row.appendChild(cell);
        elements.tableBody.appendChild(row);
    }
}

function openAddModal() {
    editingItemId = null;
    elements.form.reset();

    elements.modalTitle.textContent = "Add New Item";
    elements.saveButton.textContent = "Save Item";
    elements.itemId.disabled = false;
    elements.itemIdField.hidden = false;

    elements.modal.hidden = false;
    elements.itemId.focus();
}

function openEditModal(item) {
    editingItemId = item.id;

    elements.modalTitle.textContent = "Edit Inventory Item";
    elements.saveButton.textContent = "Update Item";

    elements.itemId.value = item.id;
    elements.itemId.disabled = true;
    elements.itemIdField.hidden = true;

    elements.itemName.value = item.name;
    elements.itemCategory.value = item.category;
    elements.itemQuantity.value = item.quantity;
    elements.itemPrice.value = item.unit_price;
    elements.itemExpiry.value = item.expiry_date || "";

    elements.modal.hidden = false;
    elements.itemName.focus();
}

function closeModal() {
    elements.modal.hidden = true;
    elements.form.reset();
    elements.itemId.disabled = false;
    elements.itemIdField.hidden = false;
    editingItemId = null;
}

async function saveItem(event) {
    event.preventDefault();

    const item = {
        name: elements.itemName.value.trim(),
        category: elements.itemCategory.value.trim(),
        quantity: Number(elements.itemQuantity.value),
        unit_price: Number(elements.itemPrice.value),
        expiry_date: elements.itemExpiry.value || null
    };

    if (!editingItemId) {
        item.id = elements.itemId.value.trim();
    }

    if (
        !item.name ||
        !item.category ||
        !Number.isFinite(item.quantity) ||
        !Number.isFinite(item.unit_price) ||
        item.quantity < 0 ||
        item.unit_price < 0
    ) {
        showMessage("Please enter valid item details.", "error");
        return;
    }

    elements.saveButton.disabled = true;
    elements.saveButton.textContent = "Saving...";

    try {
        if (editingItemId) {
            await apiRequest(
                `${API_URL}/${encodeURIComponent(editingItemId)}`,
                {
                    method: "PUT",
                    body: JSON.stringify(item)
                }
            );

            closeModal();
            await loadInventory();
            showMessage("Item updated successfully.");
        } else {
            await apiRequest(API_URL, {
                method: "POST",
                body: JSON.stringify(item)
            });

            closeModal();
            await loadInventory();
            showMessage("Item added successfully.");
        }
    } catch (error) {
        showMessage(error.message, "error");
    } finally {
        elements.saveButton.disabled = false;
        elements.saveButton.textContent =
            editingItemId ? "Update Item" : "Save Item";
    }
}

async function deleteItem(itemId) {
    const item = inventory.find(entry => entry.id === itemId);

    if (!window.confirm(
        `Are you sure you want to delete "${item?.name || itemId}"?`
    )) {
        return;
    }

    try {
        await apiRequest(
            `${API_URL}/${encodeURIComponent(itemId)}`,
            { method: "DELETE" }
        );

        await loadInventory();
        showMessage("Item deleted successfully.");
    } catch (error) {
        showMessage(error.message, "error");
    }
}

document.getElementById("addItemButton")
    .addEventListener("click", openAddModal);

document.getElementById("closeModalButton")
    .addEventListener("click", closeModal);

document.getElementById("cancelButton")
    .addEventListener("click", closeModal);

document.getElementById("refreshButton")
    .addEventListener("click", loadInventory);

elements.form.addEventListener("submit", saveItem);

elements.searchInput.addEventListener("input", applyFilters);
elements.categoryFilter.addEventListener("change", applyFilters);
elements.sortFilter.addEventListener("change", applyFilters);

elements.modal.addEventListener("click", event => {
    if (event.target === elements.modal) {
        closeModal();
    }
});

document.addEventListener("keydown", event => {
    if (event.key === "Escape" && !elements.modal.hidden) {
        closeModal();
    }
});

loadInventory();