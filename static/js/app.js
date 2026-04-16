/* ═══════════════════════════════════════════════════════
   Enterprise Portal — JavaScript
   ═══════════════════════════════════════════════════════ */

document.addEventListener('DOMContentLoaded', function () {
  // ── Sidebar toggle (mobile) ──────────────────────────
  const toggle = document.getElementById('sidebarToggle');
  const sidebar = document.getElementById('sidebar');
  const overlay = document.getElementById('sidebarOverlay');

  if (toggle && sidebar) {
    toggle.addEventListener('click', function () {
      sidebar.classList.toggle('show');
      if (overlay) overlay.classList.toggle('show');
    });
  }

  if (overlay) {
    overlay.addEventListener('click', function () {
      sidebar.classList.remove('show');
      overlay.classList.remove('show');
    });
  }

  // ── Auto-dismiss flash messages ──────────────────────
  const alerts = document.querySelectorAll('.alert-dismissible');
  alerts.forEach(function (alert) {
    setTimeout(function () {
      const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
      bsAlert.close();
    }, 5000);
  });

  // ── Delete confirmation ──────────────────────────────
  const deleteForms = document.querySelectorAll('.form-delete');
  deleteForms.forEach(function (form) {
    form.addEventListener('submit', function (e) {
      if (!confirm('Are you sure? This action cannot be undone.')) {
        e.preventDefault();
      }
    });
  });

  // ── Active sidebar link ──────────────────────────────
  const currentPath = window.location.pathname;
  const navLinks = document.querySelectorAll('.sidebar-nav .nav-link');
  navLinks.forEach(function (link) {
    const href = link.getAttribute('href');
    if (href && currentPath.startsWith(href) && href !== '/') {
      link.classList.add('active');
    }
  });

  // ── Net salary auto-calc ─────────────────────────────
  const basicField = document.getElementById('basic');
  const hraField = document.getElementById('hra');
  const deductField = document.getElementById('deductions');
  const netDisplay = document.getElementById('netSalaryDisplay');

  function calcNet() {
    if (!basicField || !netDisplay) return;
    const basic = parseFloat(basicField.value) || 0;
    const hra = parseFloat(hraField?.value) || 0;
    const deductions = parseFloat(deductField?.value) || 0;
    const net = basic + hra - deductions;
    netDisplay.textContent = '₹' + net.toLocaleString('en-IN', { minimumFractionDigits: 2 });
  }

  if (basicField) {
    [basicField, hraField, deductField].forEach(function (f) {
      if (f) f.addEventListener('input', calcNet);
    });
    calcNet();
  }

  // ── User dropdown toggle ────────────────────────────
  const dropdownBtn = document.getElementById('userDropdownBtn');
  const dropdownMenu = document.getElementById('userDropdownMenu');

  if (dropdownBtn && dropdownMenu) {
    dropdownBtn.addEventListener('click', function (e) {
      e.stopPropagation();
      dropdownMenu.classList.toggle('show');
    });

    document.addEventListener('click', function (e) {
      if (!dropdownMenu.contains(e.target) && !dropdownBtn.contains(e.target)) {
        dropdownMenu.classList.remove('show');
      }
    });
  }

  // ── Copy to clipboard (for generated passwords) ─────
  const copyBtns = document.querySelectorAll('.btn-copy');
  copyBtns.forEach(function (btn) {
    btn.addEventListener('click', function () {
      const text = btn.getAttribute('data-copy');
      if (text) {
        navigator.clipboard.writeText(text).then(function () {
          const original = btn.innerHTML;
          btn.innerHTML = '<i class="fas fa-check me-1"></i>Copied!';
          btn.classList.add('btn-success');
          btn.classList.remove('btn-outline-primary');
          setTimeout(function () {
            btn.innerHTML = original;
            btn.classList.remove('btn-success');
            btn.classList.add('btn-outline-primary');
          }, 2000);
        });
      }
    });
  });
});
