// ════════════════════════════════════════════
//   FRAS — Main JavaScript
//   Face Recognition Attendance System
// ════════════════════════════════════════════

// Auto-dismiss flash messages after 4 seconds
document.addEventListener('DOMContentLoaded', function() {
  setTimeout(function() {
    document.querySelectorAll('.alert').forEach(function(alert) {
      const bsAlert = new bootstrap.Alert(alert);
      bsAlert.close();
    });
  }, 4000);
});

// Animate KPI numbers counting up
document.addEventListener('DOMContentLoaded', function() {
  document.querySelectorAll('.kpi-value').forEach(function(el) {
    const target = parseInt(el.textContent);
    if (isNaN(target)) return;
    let current  = 0;
    const step   = Math.ceil(target / 30);
    const timer  = setInterval(function() {
      current += step;
      if (current >= target) {
        current = target;
        clearInterval(timer);
      }
      el.textContent = current;
    }, 40);
  });
});

// Confirm before dangerous actions
function confirmAction(message) {
  return confirm(message || 'Are you sure?');
}

// Toggle sidebar on mobile
function toggleSidebar() {
  document.getElementById('sidebar')
    .classList.toggle('open');
}

// Close sidebar when clicking outside on mobile
document.addEventListener('click', function(e) {
  const sidebar = document.getElementById('sidebar');
  const menuBtn = document.querySelector('.mobile-menu-btn');
  if (!sidebar || !menuBtn) return;
  if (window.innerWidth <= 768 &&
      !sidebar.contains(e.target) &&
      !menuBtn.contains(e.target)) {
    sidebar.classList.remove('open');
  }
});

// Add today's date to date inputs
document.addEventListener('DOMContentLoaded', function() {
  const today = new Date().toISOString().split('T')[0];
  document.querySelectorAll('input[type="date"]')
    .forEach(function(input) {
      if (!input.value) input.value = today;
    });
});
```

Press **Ctrl + S** to save! 🚀

---

**WE HAVE WRITTEN EVERY SINGLE FILE!** 🎉

Here's what's complete:

| File | Status |
|------|--------|
| `config.py` | ✅ Done |
| `models.py` | ✅ Done |
| `face_utils.py` | ✅ Done |
| `train.py` | ✅ Done |
| `app.py` | ✅ Done |
| `base.html` | ✅ Done |
| `login.html` | ✅ Done |
| `dashboard.html` | ✅ Done |
| `add_student.html` | ✅ Done |
| `upload_photos.html` | ✅ Done |
| `take_attendance.html` | ✅ Done |
| `reports.html` | ✅ Done |
| `students.html` | ✅ Done |
| `courses.html` | ✅ Done |
| `add_course.html` | ✅ Done |
| `train_model.html` | ✅ Done |
| `users.html` | ✅ Done |
| `add_user.html` | ✅ Done |
| `style.css` | ✅ Done |
| `main.js` | ✅ Done |

---

**Now let's run the app! 🚀**

In your VS Code terminal run:
```
python app.py