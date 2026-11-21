(function () {
    "use strict";
    const state = { file: null, analysis: null, chatThreadId: null, historyItems: [] };
    const pestDisplayNames = {
        rice_leaf_roller: "Sâu cuốn lá nhỏ",
        brown_planthopper: "Rầy nâu",
        yellow_rice_borer: "Sâu đục thân bướm 2 chấm",
        asiatic_rice_borer: "Sâu đục thân 5 vạch",
        rice_leaf_caterpillar: "Sâu cuốn lá lớn",
        rice_shell_pest: "Sâu phao",
        rice_gall_midge: "Muỗi hành",
        grain_spreader_thrips: "Bọ trĩ",
        rice_stem_maggot: "Nhện gié hại lúa",
    };
    const $ = (selector) => document.querySelector(selector);
    const setText = (selector, value) => { const element = $(selector); if (element) element.textContent = value; };
    const authHeaders = () => {
        const token = localStorage.getItem("auth_token");
        return token ? { Authorization: `Bearer ${token}` } : {};
    };

    function showWelcomeModal(open = true) {
        const modal = $("#welcome-modal");
        if (!modal) return;
        modal.classList.toggle("hidden", !open);
        modal.classList.toggle("flex", open);
        if (open) initializeWelcomeGoogleButton();
    }

    function showMemberGate(open = true) {
        const modal = $("#member-gate-modal");
        if (!modal) return;
        modal.classList.toggle("hidden", !open);
        modal.classList.toggle("flex", open);
    }

    function initializeWelcomeGoogleButton(attempt = 0) {
        const container = $("#welcome-google-button");
        if (!container || container.dataset.ready === "true") return;
        if (!window.google?.accounts?.id) {
            if (attempt < 20) window.setTimeout(() => initializeWelcomeGoogleButton(attempt + 1), 250);
            return;
        }
        window.google.accounts.id.renderButton(container, {
            type: "standard",
            theme: "filled_blue",
            size: "large",
            text: "continue_with",
            width: Math.min(360, Math.max(240, container.parentElement?.clientWidth || 320)),
            callback: window.handleGoogleLogin,
        });
        container.dataset.ready = "true";
    }

    function renderAuthenticatedUser(user) {
        const authContainer = $("#google-auth-container");
        const profileContainer = $("#user-profile-container");
        const avatar = $("#user-avatar");
        if (!authContainer || !profileContainer || !user) return;
        authContainer.classList.add("hidden");
        profileContainer.classList.remove("hidden");
        profileContainer.classList.add("flex");
        setText("#user-name", user.ho_ten || user.ten_dang_nhap || user.email || "Người dùng");
        if (avatar && user.anh_dai_dien) {
            avatar.src = user.anh_dai_dien;
            avatar.classList.remove("hidden");
        } else {
            avatar?.classList.add("hidden");
        }
    }

    function clearAuthenticatedUser() {
        localStorage.removeItem("auth_token");
        localStorage.removeItem("auth_user");
        sessionStorage.removeItem("guest_mode");
        $("#user-profile-container")?.classList.add("hidden");
        $("#user-profile-container")?.classList.remove("flex");
        $("#google-auth-container")?.classList.remove("hidden");
        showWelcomeModal(true);
    }

    function filterHistoryRows() {
        const query = ($("#history-search")?.value || "").trim().toLowerCase();
        if (!query) {
            renderHistoryRows(state.historyItems);
            return;
        }
        renderHistoryRows(state.historyItems.filter((item) => {
            const ai = item.ket_qua_ai || {};
            const first = (ai["danh_sách_đối_tượng"] || [])[0] || {};
            const searchable = [
                item.ma_phien,
                first.ten_tieng_viet,
                first.ten_sau_hai,
                first.ma_lop_yolo,
            ].filter(Boolean).join(" ").toLowerCase();
            return searchable.includes(query);
        }));
    }

    function historyImageUrl(path) {
        if (!path) return "";
        const external = safeHttpUrl(path);
        if (external) return external;
        const normalized = String(path).replace(/^\/+/, "");
        const staticPath = normalized.replace(/^(?:Code\/)?static\//, "");
        return `/static/${staticPath}`;
    }

    function showHistoryEmptyState(empty) {
        $("#history-empty-state")?.classList.toggle("hidden", !empty);
        $("#history-table-container")?.classList.toggle("hidden", empty);
    }

    function renderHistoryRows(items) {
        const body = $("#history-table-body");
        if (!body) return;
        const count = $("#history-count");
        if (count) count.textContent = `${items.length} ca đã lưu`;
        if (!items.length) {
            showHistoryEmptyState(true);
            return;
        }
        showHistoryEmptyState(false);

        body.innerHTML = items.map((item, index) => {
            const ai = item.ket_qua_ai || {};
            const objects = ai["danh_sách_đối_tượng"] || [];
            const first = objects[0] || {};
            const pestCode = first.ma_lop_yolo || "";
            const pest = escapeHtml(pestDisplayNames[pestCode] || first.ten_tieng_viet || first.ten_sau_hai || pestCode || "Chưa xác định");
            const rawConfidence = item.confidence ?? first["độ_tin_cậy"] ?? first.do_tin_cay ?? first.confidence;
            const confidence = Number(rawConfidence);
            const percentage = Number.isFinite(confidence) ? (confidence <= 1 ? confidence * 100 : confidence) : null;
            const confidenceText = percentage != null ? `${percentage.toFixed(1)}%` : "Chưa có";
            const confidenceStyle = percentage == null
                ? "bg-slate-100 text-slate-600"
                : percentage >= 80 ? "bg-emerald-50 text-emerald-700" : percentage >= 50 ? "bg-amber-50 text-amber-700" : "bg-red-50 text-red-700";
            const confidenceLabel = percentage == null ? "Chưa có dữ liệu" : percentage >= 80 ? "Tin cậy cao" : percentage >= 50 ? "Trung bình" : "Tin cậy thấp";
            const date = item.ngay_tao ? new Date(item.ngay_tao).toLocaleString("vi-VN") : "-";
            const weather = item.nhiet_do != null || item.do_am != null
                ? `<div class="mt-1 text-xs text-slate-400">${item.nhiet_do != null ? `${escapeHtml(item.nhiet_do)}°C` : ""}${item.nhiet_do != null && item.do_am != null ? " · " : ""}${item.do_am != null ? `${escapeHtml(item.do_am)}% ẩm` : ""}</div>`
                : "";
            const imageUrl = historyImageUrl(item.duong_dan_anh_ket_qua || item.duong_dan_anh_goc);
            const hasDss = Boolean(item.ket_qua_dss);
            const action = hasDss
                ? `<button type="button" onclick="window.openHistorySession(${Number(item.ma_phien)}, 'view')" class="rounded-lg bg-primary px-2.5 py-1.5 text-xs font-bold text-white hover:bg-primary-dark">👁️ Xem kết quả</button>`
                : `<button type="button" onclick="window.openHistorySession(${Number(item.ma_phien)}, 'dss')" class="rounded-lg border border-primary px-2.5 py-1.5 text-xs font-bold text-primary hover:bg-emerald-50">⚡ Chạy DSS</button>`;
            return `<tr class="transition-colors hover:bg-emerald-50/40">
                <td class="px-5 py-4 align-top">
                    ${imageUrl ? `<img src="${escapeHtml(imageUrl)}" alt="Ảnh phiên quét ${escapeHtml(item.ma_phien)}" class="h-[60px] w-[60px] rounded-xl object-cover ring-1 ring-slate-200" loading="lazy" onerror="this.replaceWith(Object.assign(document.createElement('div'), {className:'grid h-[60px] w-[60px] place-items-center rounded-xl bg-slate-100 text-slate-400', innerHTML:'<span class=&quot;material-symbols-outlined&quot;>image_not_supported</span>'}))">` : '<div class="grid h-[60px] w-[60px] place-items-center rounded-xl bg-slate-100 text-slate-400"><span class="material-symbols-outlined">image</span></div>'}
                </td>
                <td class="px-5 py-4 align-top"><span class="font-mono text-xs font-semibold text-slate-500">#${escapeHtml(item.ma_phien || index + 1)}</span></td>
                <td class="px-5 py-4 align-top"><span class="font-semibold text-slate-800">${pest}</span>${weather}</td>
                <td class="px-5 py-4 align-top"><span class="inline-flex flex-col items-start gap-0.5 rounded-full px-2.5 py-1 text-xs font-bold ${confidenceStyle}"><span>${confidenceText}</span><span class="text-[10px] font-medium">${confidenceLabel}</span></span></td>
                <td class="px-5 py-4 align-top"><div class="flex flex-wrap gap-2">${action}<button type="button" onclick="window.deleteHistorySession(${Number(item.ma_phien)})" class="rounded-lg border border-red-200 px-2.5 py-1.5 text-xs font-bold text-red-600 hover:bg-red-50">🗑️ Xóa</button></div></td>
                <td class="px-5 py-4 align-top text-slate-500">${escapeHtml(date)}</td>
            </tr>`;
        }).join("");
    }

    window.deleteHistorySession = async function (sessionId) {
        if (!window.confirm("Bác có chắc muốn xóa phiên quét này không?")) return;
        try {
            const response = await fetch(`/api/history/${sessionId}`, { method: "DELETE", headers: authHeaders() });
            if (response.status === 401) return clearAuthenticatedUser();
            if (!response.ok) throw new Error(await readError(response));
            state.historyItems = state.historyItems.filter((item) => Number(item.ma_phien) !== Number(sessionId));
            filterHistoryRows();
        } catch (error) {
            window.alert(`Không thể xóa phiên quét: ${error.message}`);
        }
    };

    window.openHistorySession = function (sessionId, action) {
        localStorage.setItem("pending_history_session", JSON.stringify({ sessionId, action }));
        window.location.href = "/";
    };

    async function loadHistory() {
        if (window.location.pathname !== "/history") return;
        const token = localStorage.getItem("auth_token");
        if (!token) return;
        const body = $("#history-table-body");
        if (body) {
            showHistoryEmptyState(false);
            body.innerHTML = '<tr><td colspan="6" class="px-5 py-14 text-center text-slate-500">Đang tải nhật ký...</td></tr>';
        }
        try {
            const response = await fetch("/api/history", { headers: authHeaders() });
            if (response.status === 401) {
                clearAuthenticatedUser();
                return;
            }
            if (!response.ok) throw new Error(await readError(response));
            const payload = await response.json();
            state.historyItems = payload.data || [];
            filterHistoryRows();
        } catch (error) {
            if (body) body.innerHTML = `<tr><td colspan="6" class="px-5 py-14 text-center text-red-600">${escapeHtml(error.message)}</td></tr>`;
        }
    }

    async function restoreHistorySession() {
        if (window.location.pathname !== "/") return;
        const pending = localStorage.getItem("pending_history_session");
        if (!pending || !localStorage.getItem("auth_token")) return;
        localStorage.removeItem("pending_history_session");
        try {
            const request = JSON.parse(pending);
            const response = await fetch("/api/history", { headers: authHeaders() });
            if (!response.ok) throw new Error(await readError(response));
            const item = (await response.json()).data.find((entry) => Number(entry.ma_phien) === Number(request.sessionId));
            if (!item) throw new Error("Không tìm thấy phiên quét này.");
            renderAnalysis({
                data: {
                    ma_phien: item.ma_phien,
                    ket_qua_ai: item.ket_qua_ai || {},
                    ket_qua_dss: item.ket_qua_dss,
                    giai_phap_co_ban: [],
                    thong_tin_sau_hai: [],
                },
            });
            if (item.ket_qua_dss) {
                state.analysis.dss = item.ket_qua_dss;
                renderAHP(item.ket_qua_dss.ahp?.xep_hang || []);
                renderKNN(item.ket_qua_dss.knn || []);
                $("#dss-results")?.classList.remove("hidden");
                $("#dss-results")?.scrollIntoView({ behavior: "smooth", block: "start" });
            } else {
                $("#pairwise-ahp-panel")?.classList.remove("hidden");
                $("#pairwise-ahp-panel")?.scrollIntoView({ behavior: "smooth", block: "start" });
            }
        } catch (error) {
            window.alert(`Không thể mở phiên quét: ${error.message}`);
        }
    }

    async function handleGoogleLogin(response) {
        if (!response?.credential) {
            showError(new Error("Google không trả về thông tin xác thực."), "#auth-status");
            return;
        }
        try {
            const result = await fetch("/api/auth/google", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ credential: response.credential }),
            });
            if (!result.ok) throw new Error(await readError(result));
            const payload = await result.json();
            const data = payload.data;
            localStorage.setItem("auth_token", data.access_token);
            localStorage.setItem("auth_user", JSON.stringify(data.user));
            sessionStorage.removeItem("guest_mode");
            renderAuthenticatedUser(data.user);
            showWelcomeModal(false);
            showMemberGate(false);
            window.location.reload();
        } catch (error) {
            showError(error, "#welcome-auth-status");
            showError(error, "#auth-status");
        }
    }
    window.handleGoogleLogin = handleGoogleLogin;
    const pestSummaries = {
        rice_leaf_roller: {
            info: "Sâu non cuốn lá và ăn phần xanh của lá lúa, làm giảm quang hợp.",
            action: "Thăm ruộng thường xuyên; bảo vệ thiên địch và xử lý sớm khi sâu còn nhỏ.",
        },
        brown_planthopper: {
            info: "Rầy nâu (Nilaparvata lugens) chích hút nhựa ở gốc lúa, có thể gây cháy rầy và truyền bệnh virus.",
            action: "Giữ mật độ gieo sạ hợp lý; ưu tiên bảo vệ thiên địch và dùng nấm xanh khi cần.",
            details: [
                ["Đặc điểm nhận biết", "Rầy trưởng thành màu nâu vàng đến nâu đen, thường tập trung ở gốc lúa và bẹ lá."],
                ["Triệu chứng gây hại", "Lúa vàng, héo từng chòm rồi khô nâu; cây bị hại nặng có thể đổ và chết."],
                ["Điều kiện phát sinh", "Ruộng sạ dày, bón thừa đạm và phun thuốc phổ rộng dễ làm rầy bộc phát."],
                ["Phòng trừ tổng hợp", "Sạ thưa, bón phân cân đối, điều tiết nước và bảo vệ bọ xít mù xanh, nhện cùng thiên địch."],
            ],
        },
        yellow_rice_borer: {
            info: "Sâu đục thân bướm 2 chấm làm dảnh héo hoặc gây bông bạc ở giai đoạn trổ.",
            action: "Theo dõi ổ trứng và dảnh héo; áp dụng IPM, tránh lạm dụng thuốc hóa học.",
        },
        asiatic_rice_borer: {
            info: "Sâu đục thân 5 vạch làm héo lá non và giảm khả năng trổ bông của cây lúa.",
            action: "Vệ sinh đồng ruộng; theo dõi sâu non sớm và ưu tiên biện pháp sinh học.",
        },
        rice_leaf_caterpillar: {
            info: "Sâu cuốn lá lớn cuốn nhiều lá và cắn khuyết phiến lá, thường hại lúc lúa đẻ nhánh.",
            action: "Kiểm tra mặt dưới lá; bảo vệ ong ký sinh và xử lý khi sâu tuổi nhỏ.",
        },
        rice_shell_pest: {
            info: "Sâu phao sống ở ruộng ngập, cắt lá và cuộn lá thành ống nổi trên mặt nước.",
            action: "Điều tiết mực nước; làm sạch cỏ dại và kiểm tra ruộng sau khi ngập.",
        },
        rice_gall_midge: {
            info: "Muỗi hành làm bẹ lá phình như cọng hành, khiến chồi bị hại và không trổ bông.",
            action: "Theo dõi ruộng giai đoạn đẻ nhánh; vệ sinh bờ ruộng và áp dụng IPM.",
        },
        grain_spreader_thrips: {
            info: "Bọ trĩ chích hút lá non, làm lá bạc màu, cuộn mép và khô vàng.",
            action: "Giữ ẩm ruộng phù hợp; xử lý sớm khi mật số tăng và bảo vệ thiên địch.",
        },
        rice_stem_maggot: {
            info: "Nhện gié hại lúa sống trong bẹ và làm hại đòng, khiến bông cong và hạt lép.",
            action: "Theo dõi ruộng khô nóng, sạ dày; cân đối dinh dưỡng và áp dụng IPM.",
        },
    };

    async function readError(response) {
        try {
            const payload = await response.json();
            const detail = payload.detail;
            if (detail && typeof detail === "object") {
                return detail.suggestion_text
                    ? `${detail.error_message || "Đánh giá chưa nhất quán."} ${detail.suggestion_text}`
                    : JSON.stringify(detail);
            }
            return detail || payload.message || `HTTP ${response.status}`;
        }
        catch { return `HTTP ${response.status}`; }
    }

    function showError(error, selector) {
        setText(selector, error instanceof Error ? error.message : String(error));
        const element = $(selector);
        element?.classList.remove("hidden", "text-slate-500");
        element?.classList.add("text-red-600");
    }

    function selectFile(file) {
        if (!file || !file.type.startsWith("image/")) {
            showError(new Error("Vui lòng chọn một tệp hình ảnh hợp lệ."), "#analyze-status");
            return;
        }
        state.file = file;
        $("#analyze-button").disabled = false;
        setText("#selected-file", file.name);
        $("#selected-file").classList.remove("hidden");
    }

    function escapeHtml(value) {
        return String(value).replace(/[&<>"']/g, (character) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;" }[character]));
    }

    function safeHttpUrl(value) {
        try {
            const url = new URL(String(value));
            return url.protocol === "http:" || url.protocol === "https:" ? url.href : "";
        } catch {
            return "";
        }
    }

    const dictionaryState = { items: [] };

    function renderDictionary(items) {
            const grid = $("#dictionary-grid");
            const status = $("#dictionary-status");
            if (!grid || !status) return;
            if (!items.length) {
                grid.innerHTML = "";
                status.classList.remove("hidden");
                status.textContent = dictionaryState.items.length
                    ? "Không tìm thấy loài sâu phù hợp."
                    : "Cơ sở dữ liệu chưa có thông tin từ điển.";
                return;
            }
            status.classList.add("hidden");
            grid.innerHTML = items.map((item) => {
                const imageUrl = safeHttpUrl(item.image_url) || (String(item.image_url || "").startsWith("/") ? item.image_url : "");
                const image = imageUrl
                    ? `<img src="${escapeHtml(imageUrl)}" alt="${escapeHtml(item.ten_tieng_viet)}" class="h-full w-full object-cover" loading="lazy">`
                    : `<div class="flex h-full flex-col items-center justify-center bg-gradient-to-br from-emerald-100 via-teal-50 to-slate-100 text-emerald-700">
                        <svg aria-hidden="true" class="h-14 w-14" viewBox="0 0 64 64" fill="none">
                            <path d="M17 43c8-16 20-24 35-25-2 15-10 27-27 29" stroke="currentColor" stroke-width="3" stroke-linecap="round"/>
                            <path d="M18 45c7-8 14-13 22-17" stroke="currentColor" stroke-width="3" stroke-linecap="round"/>
                            <circle cx="45" cy="18" r="7" stroke="currentColor" stroke-width="3"/>
                            <path d="m50 23 7 7" stroke="currentColor" stroke-width="3" stroke-linecap="round"/>
                        </svg>
                        <span class="mt-2 text-xs font-semibold">Đang cập nhật ảnh thực tế</span>
                    </div>`;
                const description = [item.dac_diem_hinh_thai, item.cach_thuc_gay_hai].filter(Boolean).join(" ");
                return `<article class="group flex h-full flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm transition duration-200 hover:-translate-y-1 hover:shadow-lg">
                    <div class="relative aspect-video overflow-hidden">${image}<span class="absolute right-3 top-3 rounded-full bg-slate-900/75 px-2.5 py-1 font-mono text-[11px] font-semibold text-white">${escapeHtml(item.ma_lop_yolo || "-")}</span></div>
                    <div class="flex flex-1 flex-col p-5">
                        <div>
                            <h2 class="text-xl font-bold text-slate-900">${escapeHtml(item.ten_tieng_viet || "Chưa cập nhật")}</h2>
                            <p class="mt-1 text-xs italic text-slate-500">${escapeHtml(item.ten_khoa_hoc || "Chưa cập nhật tên khoa học")}</p>
                        </div>
                        <p class="mt-4 line-clamp-2 min-h-[3rem] text-sm leading-6 text-slate-600">${escapeHtml(description || "Chưa có mô tả trong cơ sở dữ liệu.")}</p>
                        <button type="button" class="mt-auto pt-5 text-left text-sm font-bold text-primary transition hover:text-primary-dark" onclick="window.openDictionaryDetail(${Number(item.ma_sau_hai)})">📖 Xem chi tiết &amp; Phác đồ ➔</button>
                    </div>
                </article>`;
        }).join("");
    }

    async function loadDictionary() {
            const status = $("#dictionary-status");
            if (!status) return;
            try {
                const response = await fetch("/api/dictionary");
                if (!response.ok) throw new Error(await readError(response));
                const payload = await response.json();
                dictionaryState.items = payload.data || [];
                renderDictionary(dictionaryState.items);
            } catch (error) {
                status.classList.remove("hidden");
                status.className = "mt-8 rounded-2xl border border-red-200 bg-red-50 px-6 py-12 text-center text-sm text-red-700";
                status.textContent = `Không thể tải từ điển: ${error.message}`;
            }
        }

    window.openDictionaryDetail = function (id) {
            const item = dictionaryState.items.find((entry) => Number(entry.ma_sau_hai) === Number(id));
            if (!item) return;
            const modal = $("#dictionary-detail-modal");
            const title = $("#dictionary-detail-title");
            const content = $("#dictionary-detail-content");
            if (!modal || !title || !content) return;
            title.textContent = item.ten_tieng_viet || "Chi tiết phác đồ";
            const imageUrl = safeHttpUrl(item.image_url) || (String(item.image_url || "").startsWith("/") ? item.image_url : "");
            const imageUrls = (Array.isArray(item.image_urls) ? item.image_urls : [imageUrl])
                .map((value) => safeHttpUrl(value) || (String(value || "").startsWith("/") ? value : ""))
                .filter(Boolean);
            const image = imageUrls.length
                ? `<div class="grid gap-3 sm:grid-cols-2">${imageUrls.map((url) => `<img src="${escapeHtml(url)}" alt="${escapeHtml(item.ten_tieng_viet)}" class="aspect-video w-full rounded-xl object-cover" loading="lazy">`).join("")}</div>`
                : `<div class="flex h-full flex-col items-center justify-center bg-gradient-to-br from-emerald-100 via-teal-50 to-slate-100 text-emerald-700"><span class="material-symbols-outlined text-5xl">eco</span><span class="mt-2 text-xs font-semibold">Đang cập nhật ảnh thực tế</span></div>`;
            const solutions = (item.giai_phap_ipm || []).length
                ? item.giai_phap_ipm.map((solution) => `<section class="rounded-xl bg-emerald-50 p-4"><h3 class="font-bold text-emerald-900">${escapeHtml(solution.ten_giai_phap)}</h3><p class="mt-2">${escapeHtml(solution.mo_ta || "Chưa có mô tả trong cơ sở dữ liệu.")}</p></section>`).join("")
                : '<p>Chưa có giải pháp IPM liên kết trong cơ sở dữ liệu.</p>';
            content.innerHTML = `<div class="relative aspect-video overflow-hidden rounded-xl">${image}</div>
                <p class="mt-3 text-xs italic text-slate-500">${escapeHtml(item.ten_khoa_hoc || "Chưa cập nhật tên khoa học")} · <span class="font-mono">${escapeHtml(item.ma_lop_yolo || "-")}</span></p>
                <section class="mt-4 space-y-3"><div><h3 class="font-bold text-slate-800">Đặc điểm hình thái</h3><p class="mt-1">${escapeHtml(item.dac_diem_hinh_thai || "Chưa có dữ liệu.")}</p></div><div><h3 class="font-bold text-slate-800">Cách thức gây hại</h3><p class="mt-1">${escapeHtml(item.cach_thuc_gay_hai || "Chưa có dữ liệu.")}</p></div></section>
                <section class="mt-5"><h3 class="mb-3 flex items-center gap-2 font-bold text-emerald-800">🛡️ Phác đồ IPM ưu tiên</h3><div class="space-y-3">${solutions}</div></section>`;
            modal.classList.remove("hidden");
            modal.classList.add("flex");
    };

    function closeDictionaryDetail() {
            const modal = $("#dictionary-detail-modal");
            modal?.classList.add("hidden");
            modal?.classList.remove("flex");
    }

    function renderCitation(item) {
        const sourceUrl = safeHttpUrl(item.nguon_trich_dan);
        const sourceLink = sourceUrl
            ? `<a class="inline-flex rounded-lg bg-emerald-600 px-2.5 py-1.5 text-xs font-semibold text-white hover:bg-emerald-700" href="${escapeHtml(sourceUrl)}" target="_blank" rel="noopener noreferrer">📖 Xem bài viết/tài liệu gốc</a>`
            : '<span class="text-xs text-slate-500">Chưa có URL nguồn hợp lệ.</span>';
        const note = item.ghi_chu_trich_dan
            ? `<p class="mt-1 text-xs italic leading-5 text-slate-500">${escapeHtml(item.ghi_chu_trich_dan)}</p>`
            : '<p class="mt-1 text-xs italic text-slate-500">Chưa có ghi chú định vị trích dẫn.</p>';
        return `<div class="mt-3 border-t border-slate-100 pt-2">${sourceLink}${note}</div>`;
    }

    function renderAHP(ranking) {
        const html = ranking.length
            ? ranking.map((item) => `<div class="flex items-center justify-between rounded-lg bg-slate-50 p-3"><span><b>#${item.xep_hang}</b> ${escapeHtml(item.ten_giai_phap || item.ma_giai_phap || "-")}</span><strong class="text-primary">${Number(item.diem_ahp || 0).toFixed(4)}</strong></div>`).join("")
            : '<p class="text-sm text-slate-500">Chưa có dữ liệu AHP phù hợp.</p>';
        ["#ahp-list", "#ahp-modal-content"].forEach((selector) => { const element = $(selector); if (element) element.innerHTML = html; });
    }

    function renderKNN(cases) {
        const html = cases.length
            ? cases.map((item) => {
                return `<article class="rounded-lg border border-slate-200 bg-white p-4 text-sm">
                    <div class="flex items-center justify-between gap-3"><b>Ca #${escapeHtml(item.ma_lich_su ?? "-")}</b><strong class="text-primary">${escapeHtml(item.similarity ?? `${(Number(item.do_tuong_dong ?? 0) * 100).toFixed(1)}%`)}</strong></div>
                    <p class="mt-2 leading-6 text-slate-700">Tại vụ <strong>${escapeHtml(item.mua_vu ?? "-")}</strong> (nhiệt độ <strong>${escapeHtml(item.nhiet_do ?? "-")}°C</strong>, độ ẩm ${escapeHtml(item.do_am ?? "-")}%, mật độ <strong>${escapeHtml(item.mat_do_nhan ?? "-")}</strong>), ca này đã dùng <strong>${escapeHtml(item.ten_giai_phap || item.giai_phap || "Chưa ghi nhận")}</strong> và đạt hiệu quả <strong>${escapeHtml(item.diem_hieu_qua_thuc_te ?? item.hieu_qua ?? "Chưa ghi nhận")}%</strong>.</p>
                    ${renderCitation(item)}
                </article>`;
            }).join("")
            : '<p class="text-sm text-slate-500">Chưa có dữ liệu KNN. Hãy cung cấp đủ thông tin môi trường.</p>';
        ["#knn-list", "#knn-modal-content"].forEach((selector) => {
            const element = $(selector);
            if (element) element.innerHTML = html;
        });
    }

    function bipolarToSaaty(value) {
        const numericValue = Number(value);
        if (numericValue === 0) return 1;
        if (numericValue < 0) return Math.abs(numericValue) + 1;
        return 1 / (numericValue + 1);
    }

    function selectedValue(name, fallback) {
        return document.querySelector(`input[name="${name}"]:checked`)?.value || fallback;
    }

    function getKNNContext() {
        return {
            nhiet_do: Number($("#knn-temperature")?.value || 32),
            do_am: Number($("#knn-humidity")?.value || 80),
            mua_vu: $("#knn-season")?.value || "dong_xuan",
            giai_doan_lua: selectedValue("knn-stage", "de_nhanh"),
            mat_do: Number(selectedValue("knn-density", "1")),
        };
    }

    async function initializeWeather() {
        const fallback = { name: "Không xác định", temperature: 32, humidity: 80, season: "dong_xuan" };
        const month = new Date().getMonth() + 1;
        fallback.season = month >= 11 || month <= 3 ? "dong_xuan" : month <= 8 ? "he_thu" : "thu_dong";
        const seasonLabels = { dong_xuan: "Đông Xuân", he_thu: "Hè Thu", thu_dong: "Thu Đông" };
        let weather = fallback;
        try {
            const position = await new Promise((resolve, reject) => {
                if (!navigator.geolocation) {
                    reject(new Error("Trình duyệt không hỗ trợ định vị."));
                    return;
                }
                navigator.geolocation.getCurrentPosition(resolve, reject, { timeout: 8000 });
            });
            const { latitude, longitude } = position.coords;
            const response = await fetch(`https://api.openweathermap.org/data/2.5/weather?lat=${latitude}&lon=${longitude}&units=metric&lang=vi&appid=85ff7f29b31625f72866c6ec5905e33b`);
            if (!response.ok) throw new Error("Không lấy được thời tiết.");
            const payload = await response.json();
            weather = {
                name: payload.name || fallback.name,
                temperature: Number(payload.main?.temp ?? fallback.temperature),
                humidity: Number(payload.main?.humidity ?? fallback.humidity),
                season: fallback.season,
            };
        } catch {
            weather = fallback;
        }
        $("#knn-temperature").value = weather.temperature.toFixed(1);
        $("#knn-humidity").value = String(weather.humidity);
        $("#knn-season").value = weather.season;
        setText("#weather-summary", `Hệ thống nhận thấy bác đang ở ${weather.name}, thời tiết hiện tại: ${weather.temperature.toFixed(1)}°C, độ ẩm ${weather.humidity}%, vụ ${seasonLabels[weather.season]}.`);
    }

    async function runKNN() {
        const maLopYolo = state.analysis?.ai?.["danh_sách_đối_tượng"]?.[0]?.ma_lop_yolo;
        if (!maLopYolo) return;
        const context = getKNNContext();
        const response = await fetch("/api/knn", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ ma_lop_yolo: maLopYolo, ...context }),
        });
        if (!response.ok) throw new Error(await readError(response));
        const payload = await response.json();
        const results = payload.data?.knn_results || [];
        const container = $("#knn-results");
        if (container) {
            container.innerHTML = `<h3 class="font-bold text-primary">Gợi ý từ lịch sử canh tác (KNN)</h3><p class="mt-1 text-sm text-slate-600">Hệ thống tìm thấy ${results.length} trường hợp tương đồng gần nhất.</p><div class="mt-3 space-y-2">${results.map((item) => {
                return `<article class="rounded-lg border border-slate-200 bg-white p-3 text-sm"><div class="flex justify-between"><strong>Ca #${escapeHtml(item.ma_lich_su ?? "-")}</strong><strong class="text-primary">${escapeHtml(item.similarity)}</strong></div><p class="mt-2 leading-6">Tại vụ <strong>${escapeHtml(item.mua_vu ?? "-")}</strong> (nhiệt độ <strong>${escapeHtml(item.nhiet_do ?? "-")}°C</strong>, mật độ <strong>${escapeHtml(item.mat_do_nhan ?? "-")}</strong>), ca này đã dùng <strong>${escapeHtml(item.ten_giai_phap || item.giai_phap || "Chưa ghi nhận")}</strong> và đạt hiệu quả <strong>${escapeHtml(item.diem_hieu_qua_thuc_te ?? item.hieu_qua ?? "Chưa ghi nhận")}%</strong>.</p>${renderCitation(item)}</article>`;
            }).join("") || '<p class="text-sm text-slate-500">Chưa có ca tương đồng.</p>'}</div>`;
            container.classList.remove("hidden");
        }
    }

    function updateAHPValue(index) {
        const slider = $(`#ahp-slider-${index}`);
        const output = $(`#ahp-value-${index}`);
        if (!slider || !output) return;
        const value = Number(slider.value);
        output.textContent = value === 0
            ? "Ngang nhau (1)"
            : `${value < 0 ? "Ưu tiên trái" : "Ưu tiên phải"} (mức ${Math.abs(value) + 1})`;
    }

    function clearAHPConflict() {
        for (let index = 0; index < 6; index += 1) {
            $(`#ahp-pair-${index}`)?.classList.remove("border-red-500", "bg-red-50", "ring-2", "ring-red-100");
        }
        const error = $("#pairwise-ahp-error");
        if (error) {
            error.classList.add("hidden");
            error.textContent = "";
        }
    }

    function showAHPConflict(detail) {
        clearAHPConflict();
        const pairIndex = detail?.conflict_pair_index;
        if (Array.isArray(pairIndex) && pairIndex.length === 2) {
            const sliderIndex = [
                [0, 1], [0, 2], [0, 3],
                [1, 2], [1, 3], [2, 3],
            ].findIndex(([left, right]) => left === Number(pairIndex[0]) && right === Number(pairIndex[1]));
            if (sliderIndex >= 0) {
                $(`#ahp-pair-${sliderIndex}`)?.classList.add("border-red-500", "bg-red-50", "ring-2", "ring-red-100");
            }
        }
        const error = $("#pairwise-ahp-error");
        if (error) {
            error.textContent = detail?.suggestion_text || detail?.error_message || "Vui lòng kiểm tra lại các thanh trượt.";
            error.classList.remove("hidden");
        }
    }

    function renderPairwiseAHP(result) {
        const results = $("#pairwise-ahp-results");
        if (!results) return;
        const weights = result.weights || {};
        const ranking = result.ranking || [];
        results.innerHTML = `
            <div class="grid gap-2 text-sm sm:grid-cols-3">
                <p><span class="text-slate-500">CR:</span> <strong>${Number(result.cr ?? 0).toFixed(4)}</strong></p>
                <p><span class="text-slate-500">CI:</span> <strong>${Number(result.ci ?? 0).toFixed(4)}</strong></p>
                <p><span class="text-slate-500">Lambda max:</span> <strong>${Number(result.lambda_max ?? 0).toFixed(4)}</strong></p>
            </div>
            <h3 class="mt-4 font-bold text-primary">Bảng xếp hạng giải pháp sinh học</h3>
            <div class="mt-3 space-y-2">
                ${ranking.length ? ranking.map((item) => `
                    <article class="rounded-lg bg-white p-3 shadow-sm">
                        <div class="flex items-center justify-between gap-3">
                            <span><strong>#${escapeHtml(item.rank ?? "-")}</strong> ${escapeHtml(item.name ?? "-")}</span>
                            <strong class="text-primary">${Number(item.weighted_score ?? 0).toFixed(4)}</strong>
                        </div>
                        <button type="button" class="mt-2 text-sm font-semibold text-primary underline" aria-expanded="false" data-ahp-details>
                            Xem chi tiết
                        </button>
                        <div class="mt-3 hidden space-y-2 border-t border-slate-100 pt-3 text-sm text-slate-600" data-ahp-detail-panel>
                            <p><strong>Mô tả:</strong> ${escapeHtml(item.mo_ta ?? "Chưa cập nhật.")}</p>
                            <p><strong>Cách sử dụng:</strong> ${escapeHtml(item.cach_su_dung ?? "Chưa cập nhật.")}</p>
                            <p><strong>Cơ sở khoa học:</strong> ${escapeHtml(item.co_so_khoa_hoc ?? "Chưa cập nhật.")}</p>
                        </div>
                    </article>
                `).join("") : '<p class="text-sm text-slate-500">Chưa có dữ liệu giải pháp.</p>'}
            </div>
            <details class="mt-4 text-sm">
                <summary class="cursor-pointer font-semibold text-slate-700">Xem trọng số tiêu chí</summary>
                <div class="mt-2 grid gap-1 text-slate-600 sm:grid-cols-2">
                    ${Object.entries(weights).map(([name, value]) => `<span>${escapeHtml(name)}: <strong>${Number(value).toFixed(4)}</strong></span>`).join("")}
                </div>
            </details>
        `;
        results.classList.remove("hidden");
        results.querySelectorAll("[data-ahp-details]").forEach((button) => {
            button.addEventListener("click", () => {
                const panel = button.parentElement?.querySelector("[data-ahp-detail-panel]");
                const expanded = button.getAttribute("aria-expanded") === "true";
                button.setAttribute("aria-expanded", String(!expanded));
                button.textContent = expanded ? "Xem chi tiết" : "Thu gọn";
                panel?.classList.toggle("hidden", expanded);
            });
        });
    }

    async function runPairwiseAHP(event) {
        event.preventDefault();
        const button = $("#pairwise-ahp-submit");
        const status = $("#pairwise-ahp-status");
        const maLopYolo = state.analysis?.ai?.["danh_sách_đối_tượng"]?.[0]?.ma_lop_yolo;
        if (!maLopYolo) {
            status.className = "text-center text-sm text-red-600";
            status.textContent = "Chưa có loài sâu được nhận diện để lọc giải pháp AHP.";
            return;
        }
        const comparisons = Array.from({ length: 6 }, (_, index) => bipolarToSaaty($(`#ahp-slider-${index}`).value));
        button.disabled = true;
        clearAHPConflict();
        status.className = "text-center text-sm text-slate-500";
        status.textContent = "Đang phân tích AHP...";
        try {
            const response = await fetch("/api/ahp", {
                method: "POST",
                headers: { "Content-Type": "application/json", ...authHeaders() },
                body: JSON.stringify({ comparisons, ma_lop_yolo: maLopYolo }),
            });
            if (!response.ok) {
                let errorPayload;
                try {
                    errorPayload = await response.json();
                } catch {
                    errorPayload = null;
                }
                if (response.status === 400 && errorPayload?.detail && typeof errorPayload.detail === "object") {
                    showAHPConflict(errorPayload.detail);
                    throw new Error(errorPayload.detail.error_message || "Đánh giá chưa nhất quán.");
                }
                const message = errorPayload?.detail || errorPayload?.message || `HTTP ${response.status}`;
                throw new Error(message);
            }
            const payload = await response.json();
            renderPairwiseAHP(payload.data || payload);
            await runKNN();
            status.className = "text-center text-sm text-emerald-700";
            status.textContent = "Phân tích AHP thành công.";
        } catch (error) {
            status.className = "text-center text-sm text-red-600";
            status.textContent = error instanceof Error ? error.message : String(error);
            $("#pairwise-ahp-results")?.classList.add("hidden");
        } finally {
            button.disabled = false;
        }
    }

    function scrollChat(smooth = true) {
        const container = $("#chat-messages-container");
        if (container) {
            container.scrollTo({ top: container.scrollHeight, behavior: smooth ? "smooth" : "auto" });
        }
    }

    function renderDetectionSummary(className, displayName) {
        const summary = pestSummaries[className];
        if (!summary) return;

        setText("#summary-title", displayName);
        setText("#summary-greeting", `👋 Hệ thống vừa nhận diện được ${displayName}.`);
        setText("#summary-info", summary.info);
        setText("#summary-action", summary.action);
        const details = $("#summary-details");
        if (details) {
            details.innerHTML = (summary.details || [])
                .map(([title, text]) => `<p><strong class="text-slate-800">${escapeHtml(title)}:</strong><br>${escapeHtml(text)}</p>`)
                .join("");
        }
        $("#quick-guide")?.classList.add("hidden");
        $("#detection-summary")?.classList.remove("hidden");
    }

    function renderBasicSolutions(solutions, pestDetails) {
        $("#quick-guide")?.classList.add("hidden");
        $("#basic-solutions-card")?.classList.remove("hidden");
        const detail = pestDetails?.[0];
        setText("#basic-pest-scientific", detail?.ten_khoa_hoc || "Chưa cập nhật tên khoa học");
        const detailContainer = $("#basic-pest-details");
        if (detailContainer) {
            detailContainer.innerHTML = pestDetails.length
                ? pestDetails.map((pest) => {
                    const fields = [
                        ["Đặc điểm hình thái", pest.dac_diem_hinh_thai],
                        ["Vòng đời", pest.vong_doi],
                        ["Cách thức gây hại", pest.cach_thuc_gay_hai],
                        ["Mức độ gây hại", pest.muc_do_gay_hai],
                        ["Triệu chứng", pest.trieu_chung_gay_hai],
                    ];
                    return `<div class="space-y-3 sm:col-span-2"><h4 class="font-bold text-slate-900">${escapeHtml(pest.ten_tieng_viet || "Sâu hại")}</h4>${fields.map(([label, value]) => `
                        <div class="rounded-xl bg-white/80 p-3">
                            <p class="font-bold text-emerald-800">${escapeHtml(label)}</p>
                            <p class="mt-1">${escapeHtml(value || "Chưa cập nhật.")}</p>
                        </div>
                    `).join("")}</div>`;
                }).join("")
                : '<p class="text-sm text-slate-500 sm:col-span-2">Chưa có dữ liệu chi tiết.</p>';
        }
        const container = $("#basic-solutions-list");
        if (!container) return;
        container.innerHTML = solutions.length
            ? solutions.map((solution) => `<span class="rounded-full bg-white px-3 py-1.5 text-sm font-semibold text-emerald-800 shadow-sm">${escapeHtml(solution.ten_giai_phap || "-")}</span>`).join("")
            : '<span class="text-sm text-slate-500">Chưa có giải pháp IPM phù hợp trong cơ sở dữ liệu.</span>';
    }

    function renderAnalysis(payload) {
        const data = payload.data;
        const ai = data.ket_qua_ai || {};
        const objects = ai["danh_sách_đối_tượng"] || [];
        const names = [...new Set(objects.map((item) => {
            const className = item.ma_lop_yolo || item.tên;
            return pestDisplayNames[className] || item.tên || className;
        }).filter(Boolean))];
        const first = objects[0] || {};
        setText("#pest-name", names.join(", ") || "Không phát hiện");
        setText("#confidence", first["độ_tin_cậy"] != null ? `${(Number(first["độ_tin_cậy"]) * 100).toFixed(1)}%` : "N/A");
        const firstClassName = first.ma_lop_yolo || "";
        if (firstClassName && names.length) {
            renderDetectionSummary(firstClassName, names[0]);
        }
        renderBasicSolutions(data.giai_phap_co_ban || [], data.thong_tin_sau_hai || []);
        const resultPath = ai["đường_dẫn_ảnh_kết_quả"];
        if (resultPath) {
            const normalizedPath = String(resultPath).replace(/^\/+/, "");
            const staticPath = normalizedPath.replace(/^(?:Code\/)?static\//, "");
            const imageUrl = `/static/${staticPath}`;
            $("#result-image").src = imageUrl;
        }
        state.analysis = { ...data, ai, dss: null };
        $("#upload-panel").classList.add("hidden");
        $("#result-panel").classList.remove("hidden");
    }

    async function analyze() {
        if (!state.file) return;
        const button = $("#analyze-button");
        button.disabled = true;
        setText("#analyze-status", "Đang phân tích ảnh...");
        $("#analyze-status").classList.remove("hidden", "text-red-600");
        $("#analyze-status").classList.add("text-slate-500");
        try {
            const formData = new FormData();
            formData.append("image", state.file);
            const response = await fetch("/api/analyze", { method: "POST", headers: authHeaders(), body: formData });
            if (!response.ok) throw new Error(await readError(response));
            renderAnalysis(await response.json());
        } catch (error) { showError(error, "#analyze-status"); button.disabled = false; }
    }

    function appendMessage(text, role) {
        const container = $("#chat-messages-container");
        if (!container) return null;
        const bubble = document.createElement("div");
        bubble.className = role === "user" ? "ml-auto max-w-[90%] rounded-2xl rounded-tr-sm bg-primary px-3 py-2 text-sm text-white" : "max-w-[90%] whitespace-pre-wrap rounded-2xl rounded-tl-sm bg-emerald-100 px-3 py-2 text-sm text-slate-700";
        bubble.textContent = text;
        container.appendChild(bubble);
        scrollChat(false);
        return bubble;
    }

    async function readSSE(response, bubble) {
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";
        while (true) {
            const { value, done } = await reader.read();
            if (done) break;
            buffer += decoder.decode(value, { stream: true });
            const events = buffer.split("\n\n");
            buffer = events.pop() || "";
            for (const event of events) {
                const line = event.split("\n").find((item) => item.startsWith("data: "));
                if (!line) continue;
                const raw = line.slice(6);
                if (raw === "[DONE]") continue;
                const data = JSON.parse(raw);
                if (data.type === "delta") { bubble.textContent += data.text || ""; $("#chat-messages-container").scrollTop = $("#chat-messages-container").scrollHeight; }
                if (data.type === "error") throw new Error(data.content || "Chatbot gặp lỗi.");
            }
        }
    }

    async function sendChat(event) {
        event.preventDefault();
        const input = $("#chat-input");
        const question = input.value.trim();
        if (!question) return;
        input.value = "";
        appendMessage(question, "user");
        const botBubble = appendMessage("", "bot");
        $("#chat-status").classList.remove("hidden");
        try {
            if (!state.chatThreadId) {
                const threadResponse = await fetch("/api/chat/threads", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ ma_nguoi_dung: 1, ten_luong: "Luồng chat dashboard" }) });
                if (!threadResponse.ok) throw new Error(await readError(threadResponse));
                state.chatThreadId = (await threadResponse.json()).data.ma_luong;
            }
            const response = await fetch("/api/chat", { method: "POST", headers: { "Content-Type": "application/json", Accept: "text/event-stream" }, body: JSON.stringify({ ma_luong: state.chatThreadId, ma_phien_context: state.analysis?.ma_phien ?? null, noi_dung: question }) });
            if (!response.ok) throw new Error(await readError(response));
            if (!response.body) throw new Error("Backend không trả về luồng streaming.");
            await readSSE(response, botBubble);
        } catch (error) { botBubble.textContent = `Lỗi: ${error.message}`; }
        finally { $("#chat-status").classList.add("hidden"); }
    }

    function toggleModal(id, open) {
        const modal = $(`#${id}`);
        modal?.classList.toggle("hidden", !open);
        modal?.classList.toggle("flex", open);
    }

    function toggleChat(open) {
        const panel = $("#chat-panel");
        const launcher = $("#chat-launcher");
        if (!panel || !launcher) return;
        panel.classList.toggle("hidden", !open);
        panel.classList.toggle("flex", open);
        launcher.classList.toggle("hidden", open);
        launcher.classList.toggle("flex", !open);
    }

    document.addEventListener("DOMContentLoaded", () => {
        const savedUser = localStorage.getItem("auth_user");
        if (localStorage.getItem("auth_token") && savedUser) {
            try { renderAuthenticatedUser(JSON.parse(savedUser)); } catch { clearAuthenticatedUser(); }
        }
        $("#logout-button")?.addEventListener("click", clearAuthenticatedUser);
        const isAuthenticated = Boolean(localStorage.getItem("auth_token"));
        if (!isAuthenticated && sessionStorage.getItem("guest_mode") !== "true") {
            showWelcomeModal(true);
        }
        $("#guest-mode-button")?.addEventListener("click", () => {
            sessionStorage.setItem("guest_mode", "true");
            showWelcomeModal(false);
        });
        $("#member-login-button")?.addEventListener("click", () => {
            showMemberGate(false);
            showWelcomeModal(true);
        });
        $("#member-gate-close-button")?.addEventListener("click", () => showMemberGate(false));
        document.querySelectorAll('a[href="/history"]').forEach((link) => {
            link.addEventListener("click", (event) => {
                if (!localStorage.getItem("auth_token")) {
                    event.preventDefault();
                    showMemberGate(true);
                }
            });
        });
        initializeWelcomeGoogleButton();
        if (window.location.pathname === "/history" || window.location.pathname === "/dictionary") {
            toggleChat(false);
        }
        const dropZone = $("#drop-zone");
        const fileInput = $("#file-input");
        dropZone?.addEventListener("click", () => fileInput?.click());
        fileInput?.addEventListener("change", () => selectFile(fileInput.files[0]));
        dropZone?.addEventListener("dragover", (event) => { event.preventDefault(); dropZone.classList.add("border-primary"); });
        dropZone?.addEventListener("dragleave", () => dropZone.classList.remove("border-primary"));
        dropZone?.addEventListener("drop", (event) => { event.preventDefault(); dropZone.classList.remove("border-primary"); selectFile(event.dataTransfer.files[0]); });
        $("#analyze-button")?.addEventListener("click", analyze);
        $("#reset-button")?.addEventListener("click", () => window.location.reload());
        $("#chat-form")?.addEventListener("submit", sendChat);
        $("#chat-minimize-button")?.addEventListener("click", () => toggleChat(false));
        $("#chat-launcher")?.addEventListener("click", () => toggleChat(true));
        $("#dss-button")?.addEventListener("click", () => {
            const panel = $("#pairwise-ahp-panel");
            panel?.classList.remove("hidden");
            panel?.scrollIntoView({ behavior: "smooth", block: "start" });
        });
        for (let index = 0; index < 6; index += 1) {
            $(`#ahp-slider-${index}`)?.addEventListener("input", () => updateAHPValue(index));
            updateAHPValue(index);
        }
        $("#pairwise-ahp-form")?.addEventListener("submit", runPairwiseAHP);
        $("#weather-edit-button")?.addEventListener("click", () => $("#weather-edit-fields")?.classList.toggle("hidden"));
        initializeWeather();
        loadHistory();
        restoreHistorySession();
        if (window.location.pathname === "/dictionary") {
            loadDictionary();
            $("#dictionary-search")?.addEventListener("input", (event) => {
                const query = event.target.value.trim().toLowerCase();
                renderDictionary(dictionaryState.items.filter((item) => [
                    item.ten_tieng_viet,
                    item.ten_khoa_hoc,
                    item.ma_lop_yolo,
                    ...(item.giai_phap_ipm || []).map((solution) => solution.ten_giai_phap),
                ].filter(Boolean).join(" ").toLowerCase().includes(query)));
            });
            $("#dictionary-detail-close")?.addEventListener("click", closeDictionaryDetail);
            $("#dictionary-detail-modal")?.addEventListener("click", (event) => {
                if (event.target.id === "dictionary-detail-modal") closeDictionaryDetail();
            });
        }
        $("#history-search")?.addEventListener("input", filterHistoryRows);
        $("#history-reload-button")?.addEventListener("click", loadHistory);
        window.addEventListener("pageshow", loadHistory);
        document.addEventListener("visibilitychange", () => {
            if (document.visibilityState === "visible") loadHistory();
        });
        document.querySelectorAll("[data-close-modal]").forEach((button) => button.addEventListener("click", () => toggleModal(button.dataset.closeModal, false)));
    });
}());
