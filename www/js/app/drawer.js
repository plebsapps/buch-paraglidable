// Seitenleisten-Navigation (Etappe F2) — bewusst ohne jQuery.
// Die Inhalte bleiben die bestehenden .newModal-Elemente; aus der
// Seitenleiste geöffnet docken sie als Panel neben dem Drawer an
// (CSS-Klasse .docked) statt zentriert über der Karte zu schweben.

function toggleDrawer(force) {
    var d = document.getElementById('drawer');
    var open = (force !== undefined) ? force : d.classList.contains('closed');
    d.classList.toggle('closed', !open);
    if (!open) {
        clearDrawerActive();
        hideDockedArticles();
    }
}

function clearDrawerActive() {
    document.querySelectorAll('#drawer li').forEach(function (li) {
        li.classList.remove('active');
    });
}

function hideDockedArticles() {
    document.querySelectorAll('.newModal.docked').forEach(function (m) {
        m.style.display = 'none';
    });
}

function openArticle(modalId, navEl) {
    toggleDrawer(true);
    document.querySelectorAll('.newModal').forEach(function (m) {
        m.style.display = 'none';
    });
    var m = document.getElementById(modalId);
    m.classList.add('docked');
    m.style.display = 'inline';
    clearDrawerActive();
    if (navEl) navEl.classList.add('active');
}

// Kreuz im Panel-Titel schließt den Artikel -> aktiven Eintrag zurücksetzen
document.addEventListener('click', function (e) {
    if (e.target.classList && e.target.classList.contains('newModalTileCross')) {
        clearDrawerActive();
    }
});

// ESC schließt die Seitenleiste (Modals schließt main.js bereits)
document.addEventListener('keyup', function (e) {
    if (e.keyCode == 27 && !document.getElementById('searchInput').matches(':focus')) {
        toggleDrawer(false);
    }
});
