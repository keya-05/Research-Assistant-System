const tokenInput = document.getElementById("tokenInput");
const saveTokenButton = document.getElementById("saveTokenButton");
const tokenStatus = document.getElementById("tokenStatus");
const ticketForm = document.getElementById("ticketForm");
const emailInput = document.getElementById("emailInput");
const textInput = document.getElementById("textInput");
const createResult = document.getElementById("createResult");
const categoryFilter = document.getElementById("categoryFilter");
const statusFilter = document.getElementById("statusFilter");
const urgencyFilter = document.getElementById("urgencyFilter");
const sortFilter = document.getElementById("sortFilter");
const slaFilter = document.getElementById("slaFilter");
const searchInput = document.getElementById("searchInput");
const searchButton = document.getElementById("searchButton");
const reviewOnlyButton = document.getElementById("reviewOnlyButton");
const refreshButton = document.getElementById("refreshButton");
const listStatus = document.getElementById("listStatus");
const ticketList = document.getElementById("ticketList");
const statTotal = document.getElementById("statTotal");
const statPending = document.getElementById("statPending");
const statHigh = document.getElementById("statHigh");
const statEscalated = document.getElementById("statEscalated");
const statBreached = document.getElementById("statBreached");

const ticketCache = new Map();

function getToken() {
    return localStorage.getItem("ticketing_api_token") || "";
}

function setTokenStatus(message, isError = false) {
    tokenStatus.textContent = message;
    tokenStatus.style.color = isError ? "var(--error)" : "var(--muted)";
}

function setResult(content, isError = false) {
    createResult.classList.remove("hidden");
    createResult.classList.toggle("error", isError);
    createResult.innerHTML = content;
}

function clearResult() {
    createResult.classList.add("hidden");
    createResult.classList.remove("error");
    createResult.innerHTML = "";
}

function getHeaders() {
    const token = getToken();
    if (!token) {
        throw new Error("Please save your bearer token first.");
    }
    return {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${token}`,
    };
}

function escapeHtml(value) {
    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#39;");
}

function buildTicketUrl() {
    const params = new URLSearchParams();
    if (categoryFilter.value) {
        params.set("category", categoryFilter.value);
    }
    if (statusFilter.value) {
        params.set("status", statusFilter.value);
    }
    if (urgencyFilter.value) {
        params.set("urgency", urgencyFilter.value);
    }
    if (slaFilter.value) {
        params.set("sla_breached", slaFilter.value);
    }
    params.set("sort_by", sortFilter.value || "newest");
    return `/tickets/?${params.toString()}`;
}

async function loadStats() {
    try {
        const headers = getHeaders();
        const response = await fetch("/tickets/stats", { headers });
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.detail || "Failed to load stats.");
        }
        statTotal.textContent = data.total;
        statPending.textContent = data.pending_review;
        statHigh.textContent = data.high_priority;
        statEscalated.textContent = data.escalated;
        statBreached.textContent = data.breached;
    } catch (error) {
        statTotal.textContent = "-";
        statPending.textContent = "-";
        statHigh.textContent = "-";
        statEscalated.textContent = "-";
        statBreached.textContent = "-";
    }
}

function renderTicket(ticket) {
    const urgencyClass = ticket.urgency.toLowerCase();
    const createdAt = new Date(ticket.created_at).toLocaleString();
    const slaDueAt = new Date(ticket.sla_due_at).toLocaleString();
    const showReviewActions = ticket.status === "needs_review";
    const warningNote = ticket.urgency === "High"
        ? `<p class="warning-note">High priority ticket requires human attention.</p>`
        : "";
    const escalationNote = ticket.urgency === "High"
        ? `<p class="escalation-note">Escalation log created automatically for this ticket.</p>`
        : "";
    const slaNote = ticket.sla_breached
        ? `<p class="sla-breach-note">SLA breached for human review. Due at ${escapeHtml(slaDueAt)}.</p>`
        : `<p class="sla-note">Human review due by ${escapeHtml(slaDueAt)}.</p>`;

    return `
        <article class="ticket-card">
            <div class="ticket-topline">
                <div>
                    <div class="ticket-email">${escapeHtml(ticket.email)}</div>
                    <div class="hint">${escapeHtml(createdAt)}</div>
                </div>
                <div class="ticket-meta">
                    <span class="pill">${escapeHtml(ticket.category)}</span>
                    <span class="pill ${escapeHtml(urgencyClass)}">${escapeHtml(ticket.urgency)}</span>
                    <span class="pill">${escapeHtml(ticket.status)}</span>
                </div>
            </div>
            <div class="ticket-section">
                <h3>Ticket</h3>
                <p>${escapeHtml(ticket.text)}</p>
            </div>
            <div class="ticket-section">
                <h3>Draft Reply</h3>
                <p>${escapeHtml(ticket.draft_reply || "No draft reply generated.")}</p>
            </div>
            ${warningNote}
            ${escalationNote}
            ${slaNote}
            ${showReviewActions ? `
                <div class="review-actions">
                    <button class="primary-button" type="button" onclick="approveTicket(${ticket.id})">Approve</button>
                    <button class="secondary-button" type="button" onclick="editTicket(${ticket.id})">Edit</button>
                    <button class="secondary-button" type="button" onclick="closeTicket(${ticket.id})">Close</button>
                </div>
            ` : ""}
        </article>
    `;
}

function cacheTickets(tickets) {
    ticketCache.clear();
    tickets.forEach((ticket) => ticketCache.set(ticket.id, ticket));
}

async function loadTickets(mode = "list") {
    listStatus.style.color = "var(--muted)";
    ticketList.innerHTML = "";

    try {
        const headers = getHeaders();
        let url = buildTicketUrl();
        let loadingMessage = "Loading tickets...";

        if (mode === "review") {
            url = `/tickets/review${slaFilter.value ? `?sla_breached=${encodeURIComponent(slaFilter.value)}` : ""}`;
            loadingMessage = "Loading tickets that need review...";
        } else if (mode === "search") {
            const searchTerm = searchInput.value.trim();
            if (!searchTerm) {
                throw new Error("Enter a search term first.");
            }
            url = `/tickets/search?q=${encodeURIComponent(searchTerm)}${slaFilter.value ? `&sla_breached=${encodeURIComponent(slaFilter.value)}` : ""}`;
            loadingMessage = `Searching for "${searchTerm}"...`;
        }

        listStatus.textContent = loadingMessage;

        const response = await fetch(url, { headers });
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.detail || "Failed to load tickets.");
        }

        cacheTickets(data);
        if (data.length === 0) {
            ticketList.innerHTML = `<div class="empty-state">No tickets found for the selected view.</div>`;
            listStatus.textContent = "No tickets to display.";
            await loadStats();
            return;
        }

        ticketList.innerHTML = data.map(renderTicket).join("");
        listStatus.textContent = `${data.length} ticket${data.length === 1 ? "" : "s"} loaded.`;
        await loadStats();
    } catch (error) {
        listStatus.textContent = error.message;
        listStatus.style.color = "var(--error)";
    }
}

async function patchReview(ticketId, payload) {
    const headers = getHeaders();
    const response = await fetch(`/tickets/${ticketId}/review`, {
        method: "PATCH",
        headers,
        body: JSON.stringify(payload),
    });
    const data = await response.json();
    if (!response.ok) {
        throw new Error(data.detail || "Failed to review ticket.");
    }
    return data;
}

async function approveTicket(ticketId) {
    try {
        const data = await patchReview(ticketId, { status: "approved" });
        setResult(`
            <h3>Ticket Approved</h3>
            <p><strong>Category:</strong> ${escapeHtml(data.category)}</p>
            <p><strong>Urgency:</strong> ${escapeHtml(data.urgency)}</p>
            <p><strong>Status:</strong> ${escapeHtml(data.status)}</p>
        `);
        await loadTickets(statusFilter.value === "needs_review" ? "review" : "list");
    } catch (error) {
        setResult(`<h3>Review Failed</h3><p>${escapeHtml(error.message)}</p>`, true);
    }
}

async function closeTicket(ticketId) {
    try {
        const data = await patchReview(ticketId, { status: "closed" });
        setResult(`
            <h3>Ticket Closed</h3>
            <p><strong>Category:</strong> ${escapeHtml(data.category)}</p>
            <p><strong>Urgency:</strong> ${escapeHtml(data.urgency)}</p>
            <p><strong>Status:</strong> ${escapeHtml(data.status)}</p>
        `);
        await loadTickets(statusFilter.value === "needs_review" ? "review" : "list");
    } catch (error) {
        setResult(`<h3>Close Failed</h3><p>${escapeHtml(error.message)}</p>`, true);
    }
}

async function editTicket(ticketId) {
    const currentTicket = ticketCache.get(ticketId);
    if (!currentTicket) {
        setResult("<h3>Review Failed</h3><p>Ticket details were not found in the current view.</p>", true);
        return;
    }

    const category = window.prompt("Update category: Billing, Technical, or General", currentTicket.category);
    if (category === null) {
        return;
    }

    const urgency = window.prompt("Update urgency: High, Medium, or Low", currentTicket.urgency);
    if (urgency === null) {
        return;
    }

    const draftReply = window.prompt("Edit the draft reply before approval", currentTicket.draft_reply || "");
    if (draftReply === null) {
        return;
    }

    try {
        const data = await patchReview(ticketId, {
            category: category.trim(),
            urgency: urgency.trim(),
            draft_reply: draftReply.trim(),
            status: "approved",
        });
        setResult(`
            <h3>Ticket Reviewed</h3>
            <p><strong>Category:</strong> ${escapeHtml(data.category)}</p>
            <p><strong>Urgency:</strong> ${escapeHtml(data.urgency)}</p>
            <p><strong>Status:</strong> ${escapeHtml(data.status)}</p>
            <p><strong>Draft Reply:</strong> ${escapeHtml(data.draft_reply)}</p>
        `);
        await loadTickets(statusFilter.value === "needs_review" ? "review" : "list");
    } catch (error) {
        setResult(`<h3>Review Failed</h3><p>${escapeHtml(error.message)}</p>`, true);
    }
}

window.approveTicket = approveTicket;
window.closeTicket = closeTicket;
window.editTicket = editTicket;

saveTokenButton.addEventListener("click", async () => {
    const token = tokenInput.value.trim();
    if (!token) {
        setTokenStatus("Enter a bearer token before saving.", true);
        return;
    }
    localStorage.setItem("ticketing_api_token", token);
    setTokenStatus("Token saved. You can now submit and review tickets.");
    await loadStats();
});

ticketForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    clearResult();

    try {
        const headers = getHeaders();
        const payload = {
            email: emailInput.value.trim(),
            text: textInput.value.trim(),
        };

        const response = await fetch("/tickets/", {
            method: "POST",
            headers,
            body: JSON.stringify(payload),
        });
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.detail || "Failed to create ticket.");
        }

        setResult(`
            <h3>Ticket Created</h3>
            <p><strong>Category:</strong> ${escapeHtml(data.category)}</p>
            <p><strong>Urgency:</strong> ${escapeHtml(data.urgency)}</p>
            <p><strong>Status:</strong> ${escapeHtml(data.status)}</p>
            <p><strong>Draft Reply:</strong> ${escapeHtml(data.draft_reply)}</p>
        `);

        ticketForm.reset();
        await loadTickets();
    } catch (error) {
        setResult(`<h3>Request Failed</h3><p>${escapeHtml(error.message)}</p>`, true);
    }
});

refreshButton.addEventListener("click", async () => {
    await loadTickets();
});

reviewOnlyButton.addEventListener("click", async () => {
    statusFilter.value = "needs_review";
    sortFilter.value = "urgency";
    await loadTickets("review");
});

searchButton.addEventListener("click", async () => {
    await loadTickets("search");
});

categoryFilter.addEventListener("change", async () => {
    await loadTickets();
});

statusFilter.addEventListener("change", async () => {
    await loadTickets(statusFilter.value === "needs_review" ? "review" : "list");
});

urgencyFilter.addEventListener("change", async () => {
    await loadTickets();
});

slaFilter.addEventListener("change", async () => {
    await loadTickets(statusFilter.value === "needs_review" ? "review" : "list");
});

sortFilter.addEventListener("change", async () => {
    await loadTickets();
});

window.addEventListener("DOMContentLoaded", async () => {
    const savedToken = getToken();
    if (savedToken) {
        tokenInput.value = savedToken;
        setTokenStatus("Saved token detected.");
        await loadStats();
    }
});
