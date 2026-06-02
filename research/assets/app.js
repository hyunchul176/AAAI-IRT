/* AAAI 연구 사이트 — 공유 동작 (vanilla, 오프라인 동작) */
(function () {
  'use strict';

  /* 0) Theme: light / dark (system default + localStorage, persists across pages) */
  var root = document.documentElement;
  function curTheme() { return root.getAttribute('data-theme') || 'light'; }
  if (!root.getAttribute('data-theme')) {
    var saved = null;
    try { saved = localStorage.getItem('theme'); } catch (e) {}
    var sys = (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) ? 'dark' : 'light';
    root.setAttribute('data-theme', saved || sys);
  }
  function labelToggle(btn) {
    var dark = curTheme() === 'dark';
    btn.textContent = dark ? '☀ 라이트 모드' : '☾ 다크 모드';
    btn.setAttribute('aria-label', dark ? '라이트 모드로 전환' : '다크 모드로 전환');
  }
  document.querySelectorAll('.theme-toggle').forEach(function (btn) {
    labelToggle(btn);
    btn.addEventListener('click', function () {
      var next = curTheme() === 'dark' ? 'light' : 'dark';
      root.setAttribute('data-theme', next);
      try { localStorage.setItem('theme', next); } catch (e) {}
      document.querySelectorAll('.theme-toggle').forEach(labelToggle);
    });
  });

  /* 1) TOC scroll-spy ------------------------------------------------ */
  var tocLinks = Array.prototype.slice.call(document.querySelectorAll('.toc a[href^="#"]'));
  if (tocLinks.length) {
    var map = {};
    var targets = [];
    tocLinks.forEach(function (a) {
      var id = a.getAttribute('href').slice(1);
      var el = document.getElementById(id);
      if (el) { map[id] = a; targets.push(el); }
    });
    if ('IntersectionObserver' in window) {
      var io = new IntersectionObserver(function (entries) {
        entries.forEach(function (e) {
          if (e.isIntersecting) {
            tocLinks.forEach(function (l) { l.classList.remove('active'); });
            if (map[e.target.id]) map[e.target.id].classList.add('active');
          }
        });
      }, { rootMargin: '0px 0px -75% 0px', threshold: 0 });
      targets.forEach(function (t) { io.observe(t); });
    }
  }

  /* 2) Expand / collapse all ---------------------------------------- */
  document.querySelectorAll('[data-acc-toggle]').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var open = btn.getAttribute('data-state') !== 'open';
      document.querySelectorAll('details.acc').forEach(function (d) { d.open = open; });
      btn.setAttribute('data-state', open ? 'open' : 'closed');
      btn.textContent = open ? '모두 접기' : '모두 펼치기';
    });
  });

  /* 3) Lit-review status filter ------------------------------------- */
  var filterBtns = document.querySelectorAll('[data-filter]');
  if (filterBtns.length) {
    filterBtns.forEach(function (btn) {
      btn.addEventListener('click', function () {
        var f = btn.getAttribute('data-filter');
        filterBtns.forEach(function (b) { b.classList.toggle('active', b === btn); });
        document.querySelectorAll('[data-status]').forEach(function (card) {
          var show = (f === 'all') || card.getAttribute('data-status').split(' ').indexOf(f) !== -1;
          card.style.display = show ? '' : 'none';
        });
      });
    });
  }

  /* 4) Copy-to-clipboard for leapspace questions -------------------- */
  document.querySelectorAll('.js-copy').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var card = btn.closest('.q-card');
      var t = card && card.querySelector('.q-text');
      if (!t) return;
      var text = t.textContent.trim();
      var done = function () { var o = btn.textContent; btn.textContent = '✓ 복사됨'; setTimeout(function () { btn.textContent = o; }, 1400); };
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(done, function () { fallback(text, done); });
      } else { fallback(text, done); }
    });
  });
  function fallback(text, cb) {
    var ta = document.createElement('textarea');
    ta.value = text; ta.style.position = 'fixed'; ta.style.opacity = '0';
    document.body.appendChild(ta); ta.select();
    try { document.execCommand('copy'); cb(); } catch (e) {}
    document.body.removeChild(ta);
  }

  /* 4b) Citation popovers (click to open; outside-click / Esc to close) */
  var cites = document.querySelectorAll('.cite');
  if (cites.length) {
    var closeAllCites = function (except) {
      cites.forEach(function (c) { if (c !== except) c.classList.remove('open'); });
    };
    cites.forEach(function (c) {
      var link = c.querySelector('.cite-link');
      var pop = c.querySelector('.cite-pop');
      if (!link) return;
      link.setAttribute('tabindex', '0');
      link.addEventListener('click', function (e) {
        e.preventDefault(); e.stopPropagation();
        var was = c.classList.contains('open');
        closeAllCites(c);
        c.classList.toggle('open', !was);
      });
      link.addEventListener('keydown', function (e) {
        if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); link.click(); }
      });
      if (pop) pop.addEventListener('click', function (e) { e.stopPropagation(); });
    });
    document.addEventListener('click', function () { closeAllCites(null); });
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape') closeAllCites(null); });
  }

  /* 4c) Figure lightbox (click figure image to zoom; click/Esc to close) */
  var figImgs = document.querySelectorAll('.paper-figure img');
  if (figImgs.length) {
    var lb = document.createElement('div');
    lb.className = 'lightbox';
    lb.innerHTML = '<span class="lightbox-close" aria-label="닫기">&times;</span><img alt=""><div class="lightbox-cap"></div>';
    document.body.appendChild(lb);
    var lbImg = lb.querySelector('img');
    var lbCap = lb.querySelector('.lightbox-cap');
    var openLB = function (src, cap) {
      lbImg.src = src; lbCap.textContent = cap || '';
      lb.classList.add('open');
    };
    var closeLB = function () { lb.classList.remove('open'); lbImg.src = ''; };
    figImgs.forEach(function (img) {
      img.addEventListener('click', function () {
        var fig = img.closest('.paper-figure');
        var cap = fig ? fig.querySelector('.paper-figure-caption') : null;
        openLB(img.getAttribute('src'), cap ? cap.textContent.trim() : '');
      });
    });
    lb.addEventListener('click', closeLB);
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape') closeLB(); });
  }

  /* 4d) Figure cross-references (smooth scroll + brief highlight) ---- */
  document.querySelectorAll('a.figref[href^="#"]').forEach(function (a) {
    a.addEventListener('click', function (e) {
      var id = a.getAttribute('href').slice(1);
      var fig = document.getElementById(id);
      if (!fig) return;
      e.preventDefault();
      fig.scrollIntoView({ behavior: 'smooth', block: 'center' });
      fig.classList.remove('fig-flash');
      void fig.offsetWidth;
      fig.classList.add('fig-flash');
    });
  });

  /* 5) Live char-counter for leapspace questions (limit 500) -------- */
  document.querySelectorAll('.q-card').forEach(function (card) {
    var t = card.querySelector('.q-text');
    var c = card.querySelector('.q-count');
    if (!t || !c) return;
    var n = t.textContent.trim().length;
    c.textContent = n + ' / 500 자';
    c.classList.toggle('over', n > 500);
  });
})();
