/* ============================================================
   CARTOON AUTOMATION DASHBOARD — app.js
   Handles: Language toggle, Queue loading, Config export,
            GitHub Actions trigger, Log panel, Toast system
   ============================================================ */

'use strict';

// ===========================
//  STATE
// ===========================
let currentLang = localStorage.getItem('dash_lang') || 'ar';
let queueData   = null;

// ===========================
//  INIT
// ===========================
document.addEventListener('DOMContentLoaded', () => {
  applyLang(currentLang);
  loadStoredRepoConfig();
  loadConfigDefaults();
  setLogTime();

  // Try to auto-load queue from same directory (won't work with file://, shows hint)
  log('info', currentLang === 'ar'
    ? 'تم تحميل لوحة التحكم. استورد ملف queue.json من الزر أسفل الصفحة.'
    : 'Dashboard loaded. Import queue.json using the button at the bottom.');
});

// ===========================
//  LANGUAGE TOGGLE
// ===========================
function toggleLang() {
  currentLang = currentLang === 'ar' ? 'en' : 'ar';
  localStorage.setItem('dash_lang', currentLang);
  applyLang(currentLang);
}

function applyLang(lang) {
  const isAr = lang === 'ar';
  document.documentElement.lang  = lang;
  document.documentElement.dir   = isAr ? 'rtl' : 'ltr';
  document.body.classList.toggle('lang-en', !isAr);

  document.getElementById('lang-toggle').textContent = isAr ? '🌐 English' : '🌐 عربي';

  // Swap all data-ar / data-en text
  document.querySelectorAll('[data-ar]').forEach(el => {
    el.textContent = isAr ? el.dataset.ar : el.dataset.en;
  });

  // Re-render queue table to update labels
  if (queueData) renderQueue(queueData);
}

// ===========================
//  TOAST
// ===========================
function showToast(msg, type = 'info') {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.className = `toast show ${type === 'success' ? 'toast-success' : type === 'error' ? 'toast-error' : ''}`;
  setTimeout(() => { t.className = 'toast'; }, 3200);
}

// ===========================
//  LOG
// ===========================
function log(type, msg) {
  const panel = document.getElementById('log-panel');
  const now   = new Date().toLocaleTimeString('en-GB');
  const entry = document.createElement('div');
  entry.className = `log-entry log-${type}`;
  entry.innerHTML = `<span class="log-time">${now}</span><span class="log-msg">${escapeHtml(msg)}</span>`;
  panel.appendChild(entry);
  panel.scrollTop = panel.scrollHeight;
}

function clearLog() {
  const panel = document.getElementById('log-panel');
  panel.innerHTML = '';
  log('info', currentLang === 'ar' ? 'تم مسح السجل.' : 'Log cleared.');
}

function setLogTime() {
  const el = document.getElementById('log-initial-time');
  if (el) el.textContent = new Date().toLocaleTimeString('en-GB');
}

// ===========================
//  QUEUE FILE IMPORT
// ===========================
function handleQueueFile(event) {
  const file = event.target.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = (e) => {
    try {
      const data = JSON.parse(e.target.result);
      queueData = data;
      renderStats(data);
      renderQueue(data);
      log('success', currentLang === 'ar'
        ? `✅ تم استيراد ${file.name} بنجاح`
        : `✅ Imported ${file.name} successfully`);
      showToast(currentLang === 'ar' ? 'تم استيراد الملف ✅' : 'File imported ✅', 'success');
    } catch (err) {
      log('error', currentLang === 'ar' ? `❌ خطأ في قراءة الملف: ${err.message}` : `❌ Parse error: ${err.message}`);
      showToast(currentLang === 'ar' ? 'خطأ في الملف' : 'Invalid file', 'error');
    }
    event.target.value = '';
  };
  reader.readAsText(file);
}

// ===========================
//  STATS RENDERING
// ===========================
function renderStats(data) {
  const queue       = data.queue || [];
  const uploaded    = queue.filter(v => v.uploaded).length;
  const pending     = queue.filter(v => !v.uploaded).length;
  const totalParts  = data.total_parts || queue.length;
  const cartoonName = data.current_episode?.cartoon_name || '—';

  document.getElementById('stat-uploaded').textContent    = uploaded;
  document.getElementById('stat-pending').textContent     = pending;
  document.getElementById('stat-total-parts').textContent = totalParts;
  document.getElementById('stat-cartoon').textContent     = cartoonName;

  // Progress bar
  const pct = totalParts > 0 ? Math.round((uploaded / totalParts) * 100) : 0;
  document.getElementById('progress-fill').style.width = pct + '%';
  document.getElementById('progress-text').textContent = `${uploaded} / ${totalParts}`;

  // Badges
  const uploadedLabel = currentLang === 'ar' ? 'مرفوع' : 'uploaded';
  const pendingLabel  = currentLang === 'ar' ? 'انتظار' : 'pending';
  document.getElementById('badge-uploaded').textContent = `${uploaded} ${uploadedLabel}`;
  document.getElementById('badge-pending').textContent  = `${pending} ${pendingLabel}`;
}

// ===========================
//  QUEUE TABLE RENDERING
// ===========================
function renderQueue(data) {
  const tbody = document.getElementById('queue-tbody');
  const queue = data.queue || [];

  if (queue.length === 0) {
    tbody.innerHTML = `<tr><td colspan="6" class="empty-state">
      <div class="empty-icon">📭</div>
      <div>${currentLang === 'ar' ? 'القائمة فارغة' : 'Queue is empty'}</div>
    </td></tr>`;
    return;
  }

  tbody.innerHTML = queue.map(item => {
    const isUploaded = item.uploaded;
    const statusHtml = isUploaded
      ? `<span class="status-pill status-uploaded">✅ ${currentLang === 'ar' ? 'مرفوع' : 'Uploaded'}</span>`
      : `<span class="status-pill status-pending">⏳ ${currentLang === 'ar' ? 'انتظار' : 'Pending'}</span>`;

    const ytHtml = item.youtube_id
      ? `<a class="yt-link" href="https://youtu.be/${item.youtube_id}" target="_blank" rel="noopener">▶ ${item.youtube_id}</a>`
      : `<span style="color:#cbd5e1">—</span>`;

    const duration = formatDuration(item.duration);
    const uploadTime = item.upload_time ? formatTime(item.upload_time) : '—';

    return `<tr>
      <td><strong>${item.part_number}</strong></td>
      <td style="max-width:260px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="${escapeHtml(item.youtube_title || '')}">
        ${escapeHtml(item.youtube_title || `Part ${item.part_number}`)}
      </td>
      <td>${duration}</td>
      <td>${statusHtml}</td>
      <td>${ytHtml}</td>
      <td style="white-space:nowrap;color:var(--clr-muted);font-size:.78rem">${uploadTime}</td>
    </tr>`;
  }).join('');
}

// ===========================
//  GITHUB ACTIONS TRIGGER
// ===========================
function saveRepoConfig() {
  const repo  = document.getElementById('repo-input').value.trim();
  const token = document.getElementById('token-input').value.trim();
  if (!repo) {
    showToast(currentLang === 'ar' ? 'أدخل اسم الـ Repository' : 'Enter repository name', 'error');
    return;
  }
  localStorage.setItem('dash_repo', repo);
  if (token) localStorage.setItem('dash_token', btoa(token));
  log('success', currentLang === 'ar' ? `✅ تم حفظ إعدادات GitHub: ${repo}` : `✅ GitHub config saved: ${repo}`);
  showToast(currentLang === 'ar' ? 'تم الحفظ ✅' : 'Saved ✅', 'success');
}

function loadStoredRepoConfig() {
  const repo  = localStorage.getItem('dash_repo') || '';
  const token = localStorage.getItem('dash_token') || '';
  if (repo)  document.getElementById('repo-input').value  = repo;
  if (token) document.getElementById('token-input').value = atob(token);
}

async function triggerWorkflow(workflowId) {
  const repo  = localStorage.getItem('dash_repo') || document.getElementById('repo-input').value.trim();
  const token = (() => { try { return atob(localStorage.getItem('dash_token') || ''); } catch { return ''; } })()
              || document.getElementById('token-input').value.trim();

  if (!repo || !token) {
    showToast(currentLang === 'ar' ? '❌ أدخل Repository وToken أولاً' : '❌ Enter repository & token first', 'error');
    log('error', currentLang === 'ar' ? 'يجب إدخال Repository وToken لتشغيل Actions' : 'Repository and token required');
    return;
  }

  const btnId = workflowId === 'daily_trigger' ? 'btn-daily' : 'btn-upload';
  const btn   = document.getElementById(btnId);
  const origHtml = btn.innerHTML;
  btn.innerHTML = '<span class="spinning">↻</span>';
  btn.disabled = true;

  const workflowFile = workflowId === 'daily_trigger' ? 'daily_trigger.yml' : 'upload_scheduler.yml';
  const url = `https://api.github.com/repos/${repo}/actions/workflows/${workflowFile}/dispatches`;

  log('info', currentLang === 'ar'
    ? `⚡ جاري تشغيل ${workflowFile}...`
    : `⚡ Triggering ${workflowFile}...`);

  try {
    const res = await fetch(url, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Accept': 'application/vnd.github+json',
        'Content-Type': 'application/json',
        'X-GitHub-Api-Version': '2022-11-28'
      },
      body: JSON.stringify({ ref: 'main' })
    });

    if (res.status === 204) {
      log('success', currentLang === 'ar'
        ? `✅ تم تشغيل ${workflowFile} بنجاح!`
        : `✅ ${workflowFile} triggered successfully!`);
      showToast(currentLang === 'ar' ? `✅ تم التشغيل!` : `✅ Triggered!`, 'success');
    } else {
      const errData = await res.json().catch(() => ({}));
      const errMsg  = errData.message || `HTTP ${res.status}`;
      log('error', currentLang === 'ar' ? `❌ فشل: ${errMsg}` : `❌ Failed: ${errMsg}`);
      showToast(currentLang === 'ar' ? `❌ فشل: ${errMsg}` : `❌ Failed: ${errMsg}`, 'error');
    }
  } catch (err) {
    log('error', currentLang === 'ar'
      ? `❌ خطأ في الاتصال: ${err.message} (تأكد من CORS أو استخدم Token صحيح)`
      : `❌ Network error: ${err.message}`);
    showToast(currentLang === 'ar' ? '❌ خطأ في الاتصال' : '❌ Network error', 'error');
  } finally {
    btn.innerHTML = origHtml;
    btn.disabled  = false;
  }
}

// ===========================
//  CONFIG EDITOR
// ===========================
const DEFAULTS = {
  cartoonName: 'My Cartoon Show',
  episode:     1,
  language:    'ar',
  videoMode:   'long',
  targetDur:   50,
  minDur:      240,
  maxDur:      300,
  interval:    2,
  privacy:     'public',
  barHeight:   80,
  barColor:    '#1a1a2e',
  speedMult:   1.04,
  colorGrad:   true,
  watermark:   true,
  watermarkText: 'youcatubarx'
};

function loadConfigDefaults() {
  document.getElementById('cfg-cartoon-name').value  = DEFAULTS.cartoonName;
  document.getElementById('cfg-episode').value        = DEFAULTS.episode;
  document.getElementById('cfg-language').value       = DEFAULTS.language;
  document.getElementById('cfg-video-mode').value     = DEFAULTS.videoMode;
  document.getElementById('cfg-target-dur').value     = DEFAULTS.targetDur;
  document.getElementById('cfg-min-dur').value        = DEFAULTS.minDur;
  document.getElementById('cfg-max-dur').value        = DEFAULTS.maxDur;
  document.getElementById('cfg-interval').value       = DEFAULTS.interval;
  document.getElementById('cfg-privacy').value        = DEFAULTS.privacy;
  document.getElementById('cfg-bar-height').value     = DEFAULTS.barHeight;
  document.getElementById('cfg-bar-color').value      = DEFAULTS.barColor;
  document.getElementById('cfg-bar-color-picker').value = DEFAULTS.barColor;
  document.getElementById('cfg-speed-multiplier').value = DEFAULTS.speedMult;
  document.getElementById('cfg-color-grading').checked  = DEFAULTS.colorGrad;
  document.getElementById('cfg-watermark-enabled').checked = DEFAULTS.watermark;
  document.getElementById('cfg-watermark-text').value  = DEFAULTS.watermarkText;
  toggleModeFields();
}

function toggleModeFields() {
  const mode = document.getElementById('cfg-video-mode').value;
  const isShorts = mode === 'shorts';
  
  // Show/Hide fields based on mode
  document.querySelectorAll('.id-long-field').forEach(el => el.style.display = isShorts ? 'none' : 'block');
  document.querySelectorAll('.id-shorts-field').forEach(el => el.style.display = isShorts ? 'block' : 'none');
  
  // Hide letterbox settings when in shorts mode
  const lbGroup = document.querySelector('.id-letterbox-group');
  if (lbGroup) {
    lbGroup.style.display = isShorts ? 'none' : 'block';
  }
}

function syncColor(picker) {
  document.getElementById('cfg-bar-color').value = picker.value;
}

function syncPicker(input) {
  const val = input.value.trim();
  if (/^#[0-9a-fA-F]{6}$/.test(val)) {
    document.getElementById('cfg-bar-color-picker').value = val;
  }
}

function exportConfig() {
  const name      = document.getElementById('cfg-cartoon-name').value || DEFAULTS.cartoonName;
  const episode   = parseInt(document.getElementById('cfg-episode').value) || DEFAULTS.episode;
  const lang      = document.getElementById('cfg-language').value;
  const mode      = document.getElementById('cfg-video-mode').value || DEFAULTS.videoMode;
  const targetDur = parseInt(document.getElementById('cfg-target-dur').value) || DEFAULTS.targetDur;
  const minDur    = parseInt(document.getElementById('cfg-min-dur').value) || DEFAULTS.minDur;
  const maxDur    = parseInt(document.getElementById('cfg-max-dur').value) || DEFAULTS.maxDur;
  const interval  = parseInt(document.getElementById('cfg-interval').value) || DEFAULTS.interval;
  const privacy   = document.getElementById('cfg-privacy').value;
  const barH      = parseInt(document.getElementById('cfg-bar-height').value) || DEFAULTS.barHeight;
  const barC      = document.getElementById('cfg-bar-color').value || DEFAULTS.barColor;
  
  const speedMult = parseFloat(document.getElementById('cfg-speed-multiplier').value) || DEFAULTS.speedMult;
  const colorGrad = document.getElementById('cfg-color-grading').checked;
  const watermark = document.getElementById('cfg-watermark-enabled').checked;
  const wText     = document.getElementById('cfg-watermark-text').value || DEFAULTS.watermarkText;
  
  const nameTag   = name.toLowerCase().replace(/\s+/g, '_');

  const yaml = `# ====================================================
# إعدادات نظام أتمتة قناة الكرتون
# تم التصدير من لوحة التحكم: ${new Date().toLocaleString('ar')}
# ====================================================

cartoon:
  name: "${name}"
  episode_number: ${episode}
  language: "${lang}"

# وضع الفيديو الحالي: 'long' للفيديو العادي (16:9) أو 'shorts' للفيديوهات القصيرة (9:16)
video_mode: "${mode}"

# إعدادات الفيديوهات القصيرة (Shorts)
shorts:
  target_duration: ${targetDur}
  background_blur: true

# إعدادات الفيديوهات الطويلة (Long)
long:
  min_duration: ${minDur}
  max_duration: ${maxDur}

# إعدادات الـ Letterbox (الشريط العلوي والسفلي للوضع الطويل)
letterbox:
  bar_height: ${barH}
  bar_color: "${barC}"
  text_color: "#ffffff"
  text_font_size: 36
  logo_path: "assets/channel_banner.png"
  logo_opacity: 0.9

# إعدادات التحسينات وتجنب حقوق الملكية (Copyright Bypass)
enhancements:
  speed_multiplier: ${speedMult}
  color_grading:
    enabled: ${colorGrad}
    brightness: 0.02
    contrast: 1.03
  watermark:
    enabled: ${watermark}
    text: "${wText}"
    font_size: 24
    opacity: 0.5
    speed_x: 80
    speed_y: 40

# إعدادات يوتيوب
youtube:
  category_id: "1"
  privacy_status: "${privacy}"
  tags:
    - "كرتون"
    - "cartoon"
    - "anime"
    - "animation"
    - "${nameTag}"
  upload_interval_hours: ${interval}

# قوالب العنوان والوصف
metadata_templates:
  title: "{cartoon_name} | Episode {episode} - Part {part}"
  description: |
    🎬 {cartoon_name} - Episode {episode} | Part {part}
    
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    📺 شاهد المزيد من حلقات {cartoon_name} على قناتنا!
    🔔 اشترك في القناة وفعّل زر الجرس لتصلك كل الحلقات الجديدة
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    #cartoon #animation #{nameTag}

# إعدادات Google Drive
google_drive:
  input_folder_name: "youcut"
  processed_folder_name: "CartoonDone"

# إعدادات العمل
processing:
  temp_dir: "/tmp/cartoon_processing"
  cleanup_after_upload: true
`;

  downloadFile('config.yml', yaml, 'text/yaml');
  log('success', currentLang === 'ar'
    ? `✅ تم تصدير config.yml للكرتون: ${name}`
    : `✅ Exported config.yml for: ${name}`);
  showToast(currentLang === 'ar' ? '✅ تم تصدير config.yml' : '✅ config.yml exported', 'success');
}

// ===========================
//  REFRESH (reload queue)
// ===========================
function refreshData() {
  const btn = document.getElementById('refresh-btn');
  const icon = btn.querySelector('.btn-icon');
  icon.classList.add('spinning');
  setTimeout(() => {
    icon.classList.remove('spinning');
    if (queueData) {
      renderStats(queueData);
      renderQueue(queueData);
      log('info', currentLang === 'ar' ? '🔄 تم تحديث العرض' : '🔄 Display refreshed');
    } else {
      log('info', currentLang === 'ar'
        ? 'لا توجد بيانات محملة. استورد ملف queue.json'
        : 'No data loaded. Import queue.json first.');
    }
  }, 600);
}

// ===========================
//  HELPERS
// ===========================
function formatDuration(seconds) {
  if (!seconds) return '—';
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${String(s).padStart(2, '0')}`;
}

function formatTime(isoStr) {
  try {
    const d = new Date(isoStr);
    return d.toLocaleString(currentLang === 'ar' ? 'ar-SA' : 'en-GB', {
      month: 'short', day: 'numeric',
      hour: '2-digit', minute: '2-digit'
    });
  } catch { return '—'; }
}

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function downloadFile(filename, content, mimeType) {
  const blob = new Blob([content], { type: mimeType });
  const url  = URL.createObjectURL(blob);
  const a    = document.createElement('a');
  a.href     = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}
