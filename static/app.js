const API_URL = "/api";
let token = localStorage.getItem("access_token");
let currentLang = localStorage.getItem("lang") || "tr";
let currentTab = "expense"; // 'expense' or 'income'
let expenseChart = null;
let globalHarcamalar = [];
let globalGelirler = [];

// HTML onclick niteliklerinin çalışması için fonksiyonları global yap (En başta tanımla)
window.openCategoryModal = openCategoryModal;
window.closeCategoryModal = closeCategoryModal;
window.viewFile = viewFile;
window.closeImageModal = closeImageModal;
window.updateProfile = updateProfile;
window.changePassword = changePassword;
window.resendVerification = resendVerification;
window.changeLanguage = changeLanguage;
window.toggleSidebar = toggleSidebar;
window.toggleRightSidebar = toggleRightSidebar;
window.closeAllSidebars = closeAllSidebars;

const UI_TEXT = {
    tr: {
        dashboard: "Genel Bakış",
        recurring: "Tekrarlayan İşlemler",
        piggybank: "Kumbara",
        categories: "KATEGORİLER"
    },
    en: {
        dashboard: "Overview",
        recurring: "Recurring",
        piggybank: "Piggy Bank",
        categories: "CATEGORIES"
    }
};
function txt(key) { return UI_TEXT[currentLang]?.[key] || key; }

function toggleSidebar() {
    const sidebar = document.querySelector('.sidebar');
    const overlay = document.getElementById('sidebar-overlay');
    
    // Sağ menü açıksa kapat
    document.querySelector('.right-sidebar')?.classList.remove('active');

    if (sidebar) {
        sidebar.classList.toggle('active');
        if (sidebar.classList.contains('active')) overlay.classList.add('active');
        else overlay.classList.remove('active');
    }
}

function toggleRightSidebar() {
    const sidebar = document.querySelector('.right-sidebar');
    const overlay = document.getElementById('sidebar-overlay');
    
    // Sol menü açıksa kapat
    document.querySelector('.sidebar')?.classList.remove('active');

    if (sidebar) {
        sidebar.classList.toggle('active');
        if (sidebar.classList.contains('active')) overlay.classList.add('active');
        else overlay.classList.remove('active');
    }
}

function closeAllSidebars() {
    document.querySelector('.sidebar')?.classList.remove('active');
    document.querySelector('.right-sidebar')?.classList.remove('active');
    document.getElementById('sidebar-overlay')?.classList.remove('active');
}

// --- Başlangıç ---
document.addEventListener("DOMContentLoaded", () => {
    if (token) {
        showDashboard();
    } else {
        showAuth();
    }

    // Tarih alanına varsayılan olarak bugünü ata
    const dateInput = document.getElementById("t-date");
    if (dateInput) {
        const now = new Date();
        const day = String(now.getDate()).padStart(2, '0');
        const month = String(now.getMonth() + 1).padStart(2, '0');
        const year = now.getFullYear();
        dateInput.value = `${year}-${month}-${day}`;
    }
});

// --- Auth İşlemleri ---
const authForm = document.getElementById("auth-form");
const toggleAuthBtn = document.getElementById("toggle-auth");
let isLoginMode = true;

toggleAuthBtn.addEventListener("click", (e) => {
    e.preventDefault();
    isLoginMode = !isLoginMode;
    document.getElementById("auth-title").innerText = isLoginMode ? "Giriş Yap" : "Kayıt Ol";
    document.getElementById("submit-btn").innerText = isLoginMode ? "Giriş Yap" : "Kayıt Ol";
    document.getElementById("recovery-key").classList.toggle("hidden", isLoginMode);
    toggleAuthBtn.innerText = isLoginMode ? "Hesabın yok mu? Kayıt Ol" : "Zaten hesabın var mı? Giriş Yap";
    if (!isLoginMode) document.getElementById("recovery-key").required = true;
    else document.getElementById("recovery-key").required = false;
});

authForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const username = document.getElementById("username").value;
    const password = document.getElementById("password").value;
    const recoveryKey = document.getElementById("recovery-key").value;

    const endpoint = isLoginMode ? "/login" : "/register";
    const body = { username, password, recovery_key: recoveryKey };

    try {
        const res = await fetch(API_URL + endpoint, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body)
        });
        const data = await res.json();

        if (!res.ok) throw new Error(data.detail || "Bir hata oluştu");

        if (isLoginMode) {
            token = data.access_token;
            localStorage.setItem("access_token", token);
            localStorage.setItem("username", data.username);
            showDashboard();
        } else {
            alert("Kayıt başarılı! Şimdi giriş yapabilirsiniz.");
            location.reload();
        }
    } catch (err) {
        alert(err.message);
    }
});

function logout() {
    localStorage.removeItem("access_token");
    localStorage.removeItem("username");
    location.reload();
}

// --- Dashboard Yönetimi ---
function showAuth() {
    document.getElementById("auth-section").classList.remove("hidden");
    document.getElementById("dashboard-section").classList.add("hidden");
}

function showDashboard() {
    document.getElementById("auth-section").classList.add("hidden");
    document.getElementById("dashboard-section").classList.remove("hidden");
    
    const userDisplay = document.getElementById("user-display");
    userDisplay.innerText = localStorage.getItem("username");

    // Kullanıcı adının yanına profil ikonu ekle
    if (!document.getElementById("header-profile-icon")) {
        const icon = document.createElement("span");
        icon.id = "header-profile-icon";
        icon.innerHTML = " <span style='cursor:pointer; font-size:1.2em;' title='Profil Ayarları'>👤</span>";
        icon.onclick = () => {
            // Sidebar'daki seçimi güncelle ve profile git
            document.querySelectorAll("#sidebar-menu .menu-item").forEach(el => el.classList.remove("active"));
            switchView('profile');
        };
        userDisplay.parentNode.insertBefore(icon, userDisplay.nextSibling);
    }

    loadData();
    loadCategories();
}

async function fetchAuth(url, options = {}) {
    if (!options.headers) options.headers = {};
    options.headers["Authorization"] = `Bearer ${token}`;
    options.headers["Accept-Language"] = currentLang;
    const res = await fetch(url, options);
    if (res.status === 401) logout();
    return res;
}

async function loadData() {
    document.getElementById("loading").style.display = "block";
    try {
        // Özet
        const resOzet = await fetchAuth(API_URL + "/ozet");
        const ozet = await resOzet.json();
        document.getElementById("total-income").innerText = ozet.toplam_gelir + " ₺";
        document.getElementById("total-expense").innerText = ozet.toplam_gider + " ₺";
        document.getElementById("net-balance").innerText = ozet.net + " ₺";

        // Listeler
        const resHarcama = await fetchAuth(API_URL + "/harcamalar");
        globalHarcamalar = await resHarcama.json();
        
        const resGelir = await fetchAuth(API_URL + "/gelirler");
        globalGelirler = await resGelir.json();

        renderList(globalHarcamalar, globalGelirler);
        renderChart(globalHarcamalar);
    } catch (err) {
        console.error(err);
    } finally {
        document.getElementById("loading").style.display = "none";
    }
}

async function loadImageToElement(img, filename, placeholder) {
    try {
        const res = await fetchAuth(`${API_URL}/uploads/${filename}`);
        if (res.ok) {
            const blob = await res.blob();
            const url = URL.createObjectURL(blob);
            if (img) {
                img.src = url;
                img.style.display = "block"; // CSS class yerine doğrudan stil
                img.onclick = () => window.open(url, '_blank');
                if (placeholder) placeholder.style.display = "none";
            }
        } else {
            console.error(`Görsel sunucudan alınamadı (${res.status}): ${filename}`);
            if (placeholder) {
                placeholder.innerHTML = `<span style="color:red; font-size:0.8em;">⚠️ Yüklenemedi</span>`;
            }
        }
    } catch (e) {
        console.error("Görsel yüklenemedi:", e);
        if (placeholder) placeholder.innerText = "⚠️ Hata";
    }
}

function closeImageModal() {
    const modal = document.getElementById("image-modal");
    if(modal) {
        modal.classList.add("hidden");
        modal.style.display = "none";
        document.getElementById("modal-image-content").src = "";
    }
}

async function viewFile(filename) {
    const modal = document.getElementById("image-modal");
    const img = document.getElementById("modal-image-content");
    const link = document.getElementById("modal-download-link");
    
    // Modalı aç ve yükleniyor durumuna getir
    if(modal) {
        modal.classList.remove("hidden");
        modal.style.display = "flex";
        if(img) img.style.display = "none";
        if(link) link.style.display = "none";
    }

    try {
        const res = await fetchAuth(`${API_URL}/uploads/${filename}`);
        if (res.ok) {
            const blob = await res.blob();
            const url = URL.createObjectURL(blob);
            window.open(url, '_blank');
            
            const ext = filename.split('.').pop().toLowerCase();
            const isImage = ['jpg', 'jpeg', 'png', 'webp', 'gif', 'bmp'].includes(ext);

            if (isImage && img) {
                img.src = url;
                img.style.display = "block";
            } else if (link) {
                link.href = url;
                link.download = filename;
                link.innerText = `📄 Dosyayı İndir / Görüntüle (${ext.toUpperCase()})`;
                link.style.display = "block";
            } else {
                window.open(url, '_blank');
            }
        } else {
            alert("Dosya açılamadı.");
            alert("Dosya yüklenemedi.");
            closeImageModal();
        }
    } catch (e) {
        console.error(e);
        alert("Hata oluştu.");
        closeImageModal();
    }
}

function renderList(harcamalar, gelirler) {
    const list = document.getElementById("transaction-list");
    list.innerHTML = "";

    // Verileri birleştir ve tarihe göre sırala (basitçe)
    const all = [
        ...harcamalar.map(h => ({ ...h, type: 'expense' })),
        ...gelirler.map(g => ({ ...g, type: 'income' }))
    ].sort((a, b) => new Date(b.tarih.split('.').reverse().join('-')) - new Date(a.tarih.split('.').reverse().join('-')));

    if (all.length === 0) {
        list.innerHTML = "<p style='text-align:center; color:#888;'>Henüz işlem yok.</p>";
        return;
    }

    all.forEach(item => {
        // Hata ayıklama: Her satırın dosya bilgisini konsola yaz
        if(item.fis_dosyasi) console.log(`Dosyalı İşlem: ${item.aciklama}, Dosya: ${item.fis_dosyasi}`);

        const div = document.createElement("div");
        div.className = "list-item";
        const isExp = item.type === 'expense';
        const sign = isExp ? "-" : "+";
        const colorClass = isExp ? "minus" : "plus";
        const cat = isExp ? `<span style="background:#eee; padding:2px 6px; border-radius:4px; font-size:0.8em; margin-right:5px;">${item.kategori}</span>` : "";
        
        // Sol taraf (Açıklama, Tarih, Görsel)
        const leftDiv = document.createElement("div");
        leftDiv.innerHTML = `
            <div style="font-weight:500;">${item.aciklama}</div>
            <div style="font-size:0.85em; color:#666;">${item.tarih} ${cat}</div>
        `;

        if (isExp && item.fis_dosyasi) {
            const ext = item.fis_dosyasi.split('.').pop().toLowerCase();
            const isImage = ['jpg', 'jpeg', 'png', 'webp', 'gif', 'bmp'].includes(ext);
            
            const fileDiv = document.createElement("div");
            fileDiv.style.marginTop = "5px";

            // Her durumda dosya ismini küçük bir link olarak göster (Görsel yüklenmezse bile görünsün)
            const linkDiv = document.createElement("div");
            linkDiv.innerHTML = `<a href="#" onclick="viewFile('${item.fis_dosyasi}'); return false;" style="font-size:0.75em; color:#666; text-decoration:none;">📎 Dosya: ${item.fis_dosyasi.substring(0, 10)}...</a>`;
            fileDiv.appendChild(linkDiv);

            if (isImage) {
                const placeholder = document.createElement("div");
                placeholder.innerText = "⌛ Yükleniyor...";
                placeholder.style.fontSize = "0.8em";
                placeholder.style.color = "#888";
                placeholder.style.padding = "5px 0";
                fileDiv.appendChild(placeholder);

                const img = document.createElement("img");
                img.style.display = "none";
                img.style.maxWidth = "100px";
                img.style.maxHeight = "100px";
                img.style.borderRadius = "4px";
                img.style.cursor = "pointer";
                img.style.border = "1px solid #ddd";
                img.alt = "Fiş Görseli";
                img.title = "Büyütmek için tıkla";
                fileDiv.appendChild(img);
                loadImageToElement(img, item.fis_dosyasi, placeholder);
            } else {
                fileDiv.innerHTML = `<button type="button" onclick="viewFile('${item.fis_dosyasi}')" style="background:none; border:none; color:#4472C4; text-decoration:underline; cursor:pointer; padding:0; font-size:0.9em;">📄 Dosyayı Görüntüle (${ext.toUpperCase()})</button>`;
            }
            leftDiv.appendChild(fileDiv);
        }

        // Sağ taraf (Tutar, Butonlar)
        const rightDiv = document.createElement("div");
        rightDiv.style.textAlign = "right";
        
        let fileBtnHtml = "";
        if (isExp && item.fis_dosyasi) {
            fileBtnHtml = `<button type="button" onclick="viewFile('${item.fis_dosyasi}')" style="margin-right:5px; background-color:#8b5cf6; color:white; width:auto; padding:5px 10px; font-size:0.8em; border:none; border-radius:4px; cursor:pointer;">Fişi Gör</button>`;
        }

        rightDiv.innerHTML = `
            <div class="amount ${colorClass}">${sign}${item.tutar} ₺</div>
            ${fileBtnHtml}
            <button class="secondary edit-btn" onclick="editItem('${item.id}', '${item.type}')">Düzenle</button>
            <button class="danger" onclick="deleteItem('${item.id}', '${item.type}')">Sil</button>
        `;

        div.appendChild(leftDiv);
        div.appendChild(rightDiv);
        list.appendChild(div);
    });
}

// --- Ekleme İşlemleri ---
function switchTab(tab) {
    currentTab = tab;
    document.querySelectorAll(".tab").forEach(t => t.classList.remove("active"));
    event.target.classList.add("active");
    
    const expenseFields = document.getElementById("expense-fields");
    if (tab === 'expense') expenseFields.classList.remove("hidden");
    else expenseFields.classList.add("hidden");
}

document.getElementById("transaction-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const desc = document.getElementById("t-desc").value;
    const amount = document.getElementById("t-amount").value;
    const dateVal = document.getElementById("t-date").value;

    // Tarih formatını YYYY-MM-DD -> DD.MM.YYYY çevir
    let formattedDate = null;
    if (dateVal) {
        const parts = dateVal.split("-");
        formattedDate = `${parts[2]}.${parts[1]}.${parts[0]}`;
    }
    
    try {
        let res;
        if (currentTab === 'expense') {
            const category = document.getElementById("t-category").value;
            const fileInput = document.getElementById("t-file");
            
            const formData = new FormData();
            formData.append("aciklama", desc);
            formData.append("tutar", amount);
            formData.append("kategori", category);
            if (formattedDate) formData.append("tarih", formattedDate);
            
            if (fileInput.files[0]) {
                console.log("📤 Dosya gönderiliyor:", fileInput.files[0].name);
                formData.append("fis_dosyasi", fileInput.files[0]);
            } else {
                console.log("⚠️ Dosya seçilmedi.");
            }

            res = await fetchAuth(API_URL + "/harcamalar", {
                method: "POST",
                body: formData // Content-Type otomatik ayarlanır
            });
        } else {
            res = await fetchAuth(API_URL + "/gelirler", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ aciklama: desc, tutar: parseFloat(amount), tarih: formattedDate })
            });
        }

        if (!res.ok) throw new Error("Ekleme başarısız");
        
        document.getElementById("transaction-form").reset();
        
        // Form resetlenince tarih silinir, bugüne geri çekelim
        const now = new Date();
        const day = String(now.getDate()).padStart(2, '0');
        const month = String(now.getMonth() + 1).padStart(2, '0');
        const year = now.getFullYear();
        document.getElementById("t-date").value = `${year}-${month}-${day}`;

        loadData();
    } catch (err) {
        alert(err.message);
    }
});

async function deleteItem(id, type) {
    if (!confirm("Silmek istediğine emin misin?")) return;
    const endpoint = type === 'expense' ? `/harcamalar/${id}` : `/gelirler/${id}`;
    await fetchAuth(API_URL + endpoint, { method: "DELETE" });
    loadData();
}

function editItem(id, type) {
    alert("Düzenleme özelliği yakında eklenecek.\nID: " + id);
}

// --- Görünüm Yönetimi (View Switcher) ---
function switchView(viewName) {
    // Tüm görünümleri gizle
    ['dashboard-view', 'recurring-view', 'piggybank-view', 'profile-view'].forEach(id => {
        const el = document.getElementById(id);
        if(el) el.classList.add('hidden');
    });
    
    // Profil görünümü yoksa dinamik olarak oluştur
    if (viewName === 'profile' && !document.getElementById('profile-view')) {
        const dashboard = document.getElementById('dashboard-view');
        if (dashboard && dashboard.parentNode) {
            const profileDiv = document.createElement('div');
            profileDiv.id = 'profile-view';
            profileDiv.className = 'view-section hidden';
            dashboard.parentNode.appendChild(profileDiv);
        }
    }

    // Seçileni göster
    const target = document.getElementById(viewName + '-view');
    if(target) target.classList.remove('hidden');

    // Verileri yükle
    if (viewName === 'dashboard') {
        loadData();
    } else if (viewName === 'recurring') {
        loadRecurring();
    } else if (viewName === 'piggybank') {
        loadPiggyBank();
    } else if (viewName === 'profile') {
        loadProfile();
    }
}

async function loadCategories() {
    // 1. Önce varsayılanları HEMEN göster (Sunucuyu bekleme)
    const defaultsTr = ["Yemek", "Ulaşım", "Eğlence", "Alışveriş", "Sağlık", "Faturalar", "Diğer"];
    const defaultsEn = ["Food", "Transportation", "Entertainment", "Shopping", "Health", "Bills", "Other"];
    const defaults = currentLang === "en" ? defaultsEn : defaultsTr;
    
    // Sidebar'ı ilk kez render et (Menü öğeleriyle birlikte)
    renderSidebar(defaults); 
    
    // Tekrarlayan formundaki kategorileri de doldur
    const recSelect = document.getElementById("rec-category");
    if(recSelect) {
        recSelect.innerHTML = defaults.map(c => `<option value="${c}">${c}</option>`).join('');
    }

    const select = document.getElementById("t-category");
    if (select) {
        select.innerHTML = '<option value="Diğer">Kategori Seçiniz</option>';
        defaults.forEach(c => {
             const opt = document.createElement("option");
             opt.value = c;
             opt.innerText = c;
             select.appendChild(opt);
        });
    }

    // 2. Sonra sunucudan güncel listeyi çekmeye çalış
    try {
        const res = await fetchAuth(API_URL + "/categories");
        if (!res.ok) throw new Error("Kategoriler alınamadı");
        const cats = await res.json();
        
        // 3. Sunucudan veri geldiyse listeyi güncelle
        renderSidebar(cats);
        
        if(recSelect) {
            recSelect.innerHTML = cats.map(c => `<option value="${c}">${c}</option>`).join('');
        }
        
        if (select) {
            select.innerHTML = '<option value="Diğer">Kategori Seçiniz</option>';
            cats.forEach(c => {
                const opt = document.createElement("option");
                opt.value = c;
                opt.innerText = c;
                select.appendChild(opt);
            });
        }
    } catch (err) {
        console.error("Kategori güncellenemedi (Varsayılanlar kullanılıyor):", err);
    }
}

function renderChart(harcamalar) {
    const ctx = document.getElementById('expenseChart').getContext('2d');
    
    // Kategorilere göre grupla ve toplamları hesapla
    const categories = {};
    harcamalar.forEach(h => {
        categories[h.kategori] = (categories[h.kategori] || 0) + h.tutar;
    });

    const labels = Object.keys(categories);
    const data = Object.values(categories);
    
    // Renk paleti
    const backgroundColors = [
        '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF', '#FF9F40', '#C9CBCF', '#FF9F80', '#80B3FF'
    ];

    // Eski grafik varsa yok et (üst üste binmemesi için)
    if (expenseChart) {
        expenseChart.destroy();
    }

    expenseChart = new Chart(ctx, {
        type: 'pie',
        data: {
            labels: labels,
            datasets: [{
                data: data,
                backgroundColor: backgroundColors,
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { position: 'bottom' }
            },
            onClick: (e, elements, chart) => {
                if (elements && elements.length > 0) {
                    const index = elements[0].index;
                    const category = chart.data.labels[index];
                    filterListByCategory(category);
                } else {
                    filterListByCategory(null);
                }
            }
        }
    });
}

function renderSidebar(categories) {
    const menu = document.getElementById("sidebar-menu");
    if (!menu) return;
    menu.innerHTML = '';
    
    // 1. Ana Menü Öğeleri
    const mainItems = [
        { name: txt("dashboard"), icon: "📊", action: () => { switchView('dashboard'); handleSidebarClick(null, null); } },
        { name: txt("recurring"), icon: "🔄", action: () => switchView('recurring') },
        { name: txt("piggybank"), icon: "🐖", action: () => switchView('piggybank') }
    ];

    mainItems.forEach(item => {
        const div = document.createElement("div");
        div.className = "menu-item";
        if (item.name === "Genel Bakış") div.classList.add("active"); // Varsayılan aktif
        div.innerHTML = `<span style="margin-right:8px;">${item.icon}</span> ${item.name}`;
        div.onclick = () => {
            document.querySelectorAll("#sidebar-menu .menu-item").forEach(el => el.classList.remove("active"));
            div.classList.add("active");
            item.action();
            if (window.innerWidth <= 1024) toggleSidebar(); // Mobilde tıklandığında menüyü kapat
        };
        menu.appendChild(div);
    });

    // Ayırıcı
    const hr = document.createElement("hr");
    hr.style.margin = "10px 0";
    hr.style.border = "0";
    hr.style.borderTop = "1px solid #eee";
    menu.appendChild(hr);

    const catTitle = document.createElement("div");
    catTitle.style.padding = "5px 12px";
    catTitle.style.fontSize = "0.85em";
    catTitle.style.color = "#888";
    catTitle.innerText = txt("categories");
    menu.appendChild(catTitle);

    // 2. Kategoriler
    categories.forEach(cat => {
        const item = document.createElement("div");
        item.className = "menu-item";
        item.innerText = cat;
        item.onclick = () => {
            document.querySelectorAll("#sidebar-menu .menu-item").forEach(el => el.classList.remove("active"));
            item.classList.add("active");
            
            // switchView('dashboard') yerine manuel geçiş yapıyoruz ki loadData() çalışıp filtreyi ezmesin.
            ['dashboard-view', 'recurring-view', 'piggybank-view', 'profile-view'].forEach(id => {
                const el = document.getElementById(id);
                if(el) el.classList.add('hidden');
            });
            document.getElementById('dashboard-view').classList.remove('hidden');
            
            handleSidebarClick(cat, item);
            if (window.innerWidth <= 1024) toggleSidebar(); // Mobilde tıklandığında menüyü kapat
        };
        menu.appendChild(item);
    });
}

function handleSidebarClick(category, element) {
    if (category) {
        // Kategoriye göre filtrele
        filterListByCategory(category);
        
        // Özeti güncelle (Sadece o kategori için)
        const total = globalHarcamalar
            .filter(h => h.kategori === category)
            .reduce((sum, h) => sum + h.tutar, 0);
            
        document.querySelector(".summary-item.expense small").innerText = category + " Toplamı";
        document.getElementById("total-expense").innerText = total + " ₺";
        
        // Gelir ve Kalan kısımlarını soluklaştır
        document.querySelector(".summary-item.income").style.opacity = "0.3";
        document.querySelector(".summary-item:last-child").style.opacity = "0.3";
        
        // Ekleme formunda kategoriyi seç
        const select = document.getElementById("t-category");
        if(select) select.value = category;
    } else {
        // Genel bakışa dön
        document.querySelector(".summary-item.expense small").innerText = "Gider";
        document.querySelector(".summary-item.income").style.opacity = "1";
        document.querySelector(".summary-item:last-child").style.opacity = "1";
        
        // Ekleme formundaki kategori seçimini varsayılana döndür
        const select = document.getElementById("t-category");
        if(select) select.value = "Diğer";

        loadData(); // Verileri ve özeti tazelemek için
    }
}

function filterListByCategory(category) {
    if (!category) {
        renderList(globalHarcamalar, globalGelirler);
        return;
    }
    const filtered = globalHarcamalar.filter(h => h.kategori === category);
    renderList(filtered, []); // Sadece o kategorideki harcamaları göster
}

// --- Kategori Modal İşlemleri ---
function openCategoryModal() {
    const modal = document.getElementById("category-modal");
    modal.classList.remove("hidden");
    modal.style.display = "flex";
}

function closeCategoryModal() {
    const modal = document.getElementById("category-modal");
    modal.classList.add("hidden");
    modal.style.display = "none";
}

// Modal dışına tıklanınca kapat
window.addEventListener("click", (event) => {
    const modal = document.getElementById("category-modal");
    const imgModal = document.getElementById("image-modal");
    if (event.target == modal) {
        closeCategoryModal();
    }
    if (event.target == imgModal) {
        closeImageModal();
    }
});

document.addEventListener("DOMContentLoaded", () => {
 const form = document.getElementById("add-category-form");
 if(form) form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const name = document.getElementById("new-category-name").value;
    
    try {
        const res = await fetchAuth(API_URL + "/categories", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ name })
        });
        
        if (!res.ok) throw new Error("Kategori eklenemedi");
        
        document.getElementById("add-category-form").reset();
        closeCategoryModal();
        loadCategories(); // Listeyi güncelle
    } catch (err) {
        alert(err.message);
    }
 });

 // Tekrarlayan İşlemler Formu
 const recForm = document.getElementById("recurring-form");
 if(recForm) recForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const body = {
        aciklama: document.getElementById("rec-desc").value,
        tutar: parseFloat(document.getElementById("rec-amount").value),
        gun: intVal = parseInt(document.getElementById("rec-day").value),
        kategori: document.getElementById("rec-category").value,
        aktif: true
    };
    await fetchAuth(API_URL + "/tekrarlayan", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body)
    });
    recForm.reset();
    loadRecurring();
 });

 // Kumbara Ayar Formu
 const piggyForm = document.getElementById("piggy-settings-form");
 if(piggyForm) piggyForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const mode = document.getElementById("piggy-mode").value;
    const amount = parseFloat(document.getElementById("piggy-amount").value) || 0;
    const goalDesc = document.getElementById("piggy-goal-desc").value;
    const goalAmount = parseFloat(document.getElementById("piggy-goal-amount").value) || 0;
    
    const body = {
        mod: mode || null,
        gunluk_tutar: mode === 'gunluk' ? amount : 0,
        haftalik_tutar: mode === 'haftalik' ? amount : 0,
        hedef_tutar: goalAmount,
        hedef_aciklama: goalDesc
    };
    
    await fetchAuth(API_URL + "/kumbara/ayarlar", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body)
    });
    alert("Ayarlar kaydedildi!");
    loadPiggyBank();
 });
});

// --- Tekrarlayan İşlemler Fonksiyonları ---
async function loadRecurring() {
    const res = await fetchAuth(API_URL + "/tekrarlayan");
    const data = await res.json();
    const list = document.getElementById("recurring-list");
    list.innerHTML = "";
    
    data.forEach((item, index) => {
        const div = document.createElement("div");
        div.className = "list-item";
        div.innerHTML = `
            <div>
                <strong>${item.aciklama}</strong> <small>(${item.kategori})</small><br>
                <span style="color:#666; font-size:0.9em;">Her ayın ${item.gun}. günü</span>
            </div>
            <div>
                <span class="amount minus">-${item.tutar} ₺</span>
                <button class="danger" onclick="deleteRecurring(${index})">Sil</button>
            </div>
        `;
        list.appendChild(div);
    });
}

async function deleteRecurring(index) {
    if(!confirm("Silmek istediğine emin misin?")) return;
    await fetchAuth(API_URL + `/tekrarlayan/${index}`, { method: "DELETE" });
    loadRecurring();
}

// --- Kumbara Fonksiyonları ---
async function loadPiggyBank() {
    const res = await fetchAuth(API_URL + "/kumbara");
    const data = await res.json();
    
    document.getElementById("piggy-balance").innerText = data.bakiye.toFixed(2) + " ₺";
    document.getElementById("piggy-mode").value = data.ayar.mod || "";
    document.getElementById("piggy-amount").value = data.ayar.mod === 'gunluk' ? data.ayar.gunluk_tutar : data.ayar.haftalik_tutar;
    
    // Hedef alanlarını doldur
    document.getElementById("piggy-goal-desc").value = data.ayar.hedef_aciklama || "";
    document.getElementById("piggy-goal-amount").value = data.ayar.hedef_tutar || "";

    // Hedef göstergesini güncelle
    const goalContainer = document.getElementById("piggy-goal-container");
    if (data.ayar.hedef_tutar > 0) {
        goalContainer.classList.remove("hidden");
        const percent = Math.min(100, (data.bakiye / data.ayar.hedef_tutar) * 100);
        document.getElementById("piggy-goal-text").innerText = "Hedef: " + (data.ayar.hedef_aciklama || "Belirtilmemiş");
        document.getElementById("piggy-goal-status").innerText = `${data.bakiye.toFixed(2)} / ${data.ayar.hedef_tutar} ₺ (%${percent.toFixed(1)})`;
        document.getElementById("piggy-goal-bar").style.width = percent + "%";
    } else {
        goalContainer.classList.add("hidden");
    }
    
    const history = document.getElementById("piggy-history");
    history.innerHTML = "";
    data.islemler.reverse().slice(0, 10).forEach(i => {
        const div = document.createElement("div");
        div.className = "list-item";
        const color = i.tur === 'ekle' ? 'plus' : 'minus';
        const sign = i.tur === 'ekle' ? '+' : '-';
        div.innerHTML = `
            <div>${i.tarih} - ${i.aciklama || 'İşlem'}</div>
            <div class="amount ${color}">${sign}${i.tutar} ₺</div>
        `;
        history.appendChild(div);
    });
}

async function piggyAction(type) {
    const amount = prompt(type === 'ekle' ? "Eklenecek tutar:" : "Çekilecek tutar:");
    if(!amount) return;
    await fetchAuth(API_URL + "/kumbara/islem", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ tutar: parseFloat(amount), tur: type })
    });
    loadPiggyBank();
}

// --- Profil İşlemleri ---
async function loadProfile() {
    const container = document.getElementById('profile-view');
    if(!container) return;
    
    container.innerHTML = '<div style="text-align:center; padding:20px;">Yükleniyor...</div>';
    
    try {
        const res = await fetchAuth(API_URL + "/profile");
        if(!res.ok) throw new Error("Profil bilgileri alınamadı");
        const data = await res.json();
        
        container.innerHTML = `
            <div style="max-width:600px; margin:0 auto;">
                <h2 style="margin-bottom:20px; border-bottom:1px solid #eee; padding-bottom:10px;">Profil Ayarları</h2>
                
                <div class="card" style="background:white; padding:20px; border-radius:8px; box-shadow:0 2px 4px rgba(0,0,0,0.05); margin-bottom:20px;">
                    <h3 style="margin-top:0;">Kullanıcı Bilgileri</h3>
                    <form onsubmit="updateProfile(event)">
                        <div style="margin-bottom:15px;">
                            <label style="display:block; margin-bottom:5px; font-weight:500;">Kullanıcı Adı</label>
                            <input type="text" value="${localStorage.getItem('username')}" disabled style="width:100%; padding:8px; background:#f5f5f5; border:1px solid #ddd; border-radius:4px;">
                        </div>
                        <div style="margin-bottom:15px;">
                            <label style="display:block; margin-bottom:5px; font-weight:500;">E-posta</label>
                            <input type="email" id="p-email" value="${data.email || ''}" required style="width:100%; padding:8px; border:1px solid #ddd; border-radius:4px;">
                            <div style="margin-top:5px; font-size:0.9em;">
                                ${data.is_verified ? 
                                    '<span style="color:green">✓ E-posta doğrulanmış</span>' : 
                                    '<span style="color:#f59e0b">⚠️ Doğrulanmamış</span> ' + (data.email ? '<button type="button" onclick="resendVerification()" style="background:none; border:none; color:#4472C4; text-decoration:underline; cursor:pointer;">Doğrulama Linki Gönder</button>' : '')}
                            </div>
                        </div>
                        <button type="submit" style="background:#4472C4; color:white; border:none; padding:10px 20px; border-radius:4px; cursor:pointer;">Bilgileri Güncelle</button>
                    </form>
                </div>
                
                <div class="card" style="background:white; padding:20px; border-radius:8px; box-shadow:0 2px 4px rgba(0,0,0,0.05); margin-bottom:20px;">
                    <h3 style="margin-top:0;">Dil / Language</h3>
                    <div style="display:flex; gap:10px;">
                        <button type="button" onclick="changeLanguage('tr')" style="flex:1; padding:10px; border:1px solid ${currentLang==='tr'?'#4472C4':'#ddd'}; border-radius:4px; background:${currentLang==='tr'?'#eef2ff':'white'}; cursor:pointer;">
                            🇹🇷 Türkçe ${currentLang==='tr'?'(Seçili)':''}
                        </button>
                        <button type="button" onclick="changeLanguage('en')" style="flex:1; padding:10px; border:1px solid ${currentLang==='en'?'#4472C4':'#ddd'}; border-radius:4px; background:${currentLang==='en'?'#eef2ff':'white'}; cursor:pointer;">
                            🇬🇧 English ${currentLang==='en'?'(Selected)':''}
                        </button>
                    </div>
                </div>

                <div class="card" style="background:white; padding:20px; border-radius:8px; box-shadow:0 2px 4px rgba(0,0,0,0.05);">
                    <h3 style="margin-top:0;">Şifre Değiştir</h3>
                    <form onsubmit="changePassword(event)">
                        <div style="margin-bottom:15px;">
                            <label style="display:block; margin-bottom:5px; font-weight:500;">Mevcut Şifre</label>
                            <input type="password" id="pw-old" required style="width:100%; padding:8px; border:1px solid #ddd; border-radius:4px;">
                        </div>
                        <div style="margin-bottom:15px;">
                            <label style="display:block; margin-bottom:5px; font-weight:500;">Yeni Şifre</label>
                            <input type="password" id="pw-new" required style="width:100%; padding:8px; border:1px solid #ddd; border-radius:4px;">
                        </div>
                        <button type="submit" style="background:#666; color:white; border:none; padding:10px 20px; border-radius:4px; cursor:pointer;">Şifreyi Değiştir</button>
                    </form>
                </div>
            </div>
        `;
    } catch (e) {
        container.innerHTML = `<p style="color:red; text-align:center;">Hata: ${e.message}</p>`;
    }
}

async function updateProfile(e) {
    e.preventDefault();
    const email = document.getElementById('p-email').value;
    try {
        const res = await fetchAuth(API_URL + "/profile", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email })
        });
        if(!res.ok) throw new Error("Güncelleme başarısız");
        alert("Profil güncellendi!");
        loadProfile();
    } catch(err) {
        alert(err.message);
    }
}

async function changePassword(e) {
    e.preventDefault();
    const oldPw = document.getElementById('pw-old').value;
    const newPw = document.getElementById('pw-new').value;
    try {
        const res = await fetchAuth(API_URL + "/change-password", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ 
                username: localStorage.getItem('username'),
                old_password: oldPw,
                new_password: newPw
            })
        });
        const data = await res.json();
        if(!res.ok) throw new Error(data.detail || "Hata oluştu");
        alert("Şifre başarıyla değiştirildi!");
        document.getElementById('pw-old').value = "";
        document.getElementById('pw-new').value = "";
    } catch(err) {
        alert(err.message);
    }
}

async function resendVerification() {
    try {
        const res = await fetchAuth(API_URL + "/resend-verification", { method: "POST" });
        const data = await res.json();
        alert(data.message);
    } catch(err) {
        alert("İşlem başarısız");
    }
}

function changeLanguage(lang) {
    localStorage.setItem("lang", lang);
    location.reload();
}

// --- OCR (Fiş Okuma) ---
async function handleOcrUpload(input) {
    if (!input.files || !input.files[0]) return;
    
    const overlay = document.getElementById("ocr-loading");
    if(overlay) {
        overlay.classList.remove("hidden");
        overlay.style.display = "flex";
    }

    const formData = new FormData();
    formData.append("file", input.files[0]);
    
    try {
        const res = await fetchAuth(API_URL + "/harcamalar/otomatik-fis", {
            method: "POST",
            body: formData
        });
        if(!res.ok) throw new Error("Okuma başarısız");
        await res.json();
        loadData();
        showToast("Fiş başarıyla eklendi!");
    } catch(e) {
        alert("Hata: " + e.message);
    } finally {
        if(overlay) {
            overlay.classList.add("hidden");
            overlay.style.display = "none";
        }
        input.value = ""; // Reset
    }
}

function showToast(message) {
    const x = document.getElementById("toast");
    if (!x) return;
    x.innerText = message;
    x.className = "show";
    setTimeout(function(){ x.className = x.className.replace("show", ""); }, 3000);
}