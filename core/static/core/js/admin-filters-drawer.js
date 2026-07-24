/*
 * Daily Reports admin — drawer-based filter UX.
 *   - Hero "Filters" button opens Unfold's off-canvas drawer (via Alpine.js).
 *   - Any change inside the drawer auto-submits the filter form; no Apply button.
 *   - Drawer is kept open across the submit → users can layer multiple filters
 *     without reopening it every time.
 *   - Unfold's default toolbar Filters button is hidden (hero button replaces it).
 */
(function () {
    "use strict";

    var SESSION_KEY = "ngs-dr-filter-open";

    function ready(fn) {
        if (document.readyState !== "loading") {
            fn();
        } else {
            document.addEventListener("DOMContentLoaded", fn);
        }
    }

    function hideDefaultFilterTriggers() {
        var triggers = document.querySelectorAll(
            '[x-on\\:click="filterOpen = true"]'
        );
        triggers.forEach(function (el) {
            if (el.id === "ngs-dr-filter-btn") {
                return;
            }
            el.setAttribute("hidden", "hidden");
            el.style.display = "none";
        });
    }

    function openDrawer() {
        var btn = document.getElementById("ngs-dr-filter-btn");
        if (!btn) {
            return;
        }
        btn.click();
    }

    function bindAutoSubmit() {
        var form = document.getElementById("filter-form");
        if (!form) {
            return;
        }

        var applyBtn = form.querySelector('button[type="submit"]');
        if (applyBtn) {
            applyBtn.style.display = "none";
        }

        var timer = null;

        function scheduleSubmit() {
            sessionStorage.setItem(SESSION_KEY, "1");
            if (timer) {
                clearTimeout(timer);
            }
            timer = setTimeout(function () {
                form.submit();
            }, 220);
        }

        form.addEventListener("change", function (evt) {
            var target = evt.target;
            if (!target) {
                return;
            }
            if (
                target.matches(
                    'select, input[type="checkbox"], input[type="radio"], input[type="date"], input[type="number"]'
                )
            ) {
                scheduleSubmit();
            }
        });

        form.addEventListener("input", function (evt) {
            var target = evt.target;
            if (
                target &&
                target.matches('input[type="text"], input[type="search"], input[type="date"]')
            ) {
                scheduleSubmit();
            }
        });

        form.addEventListener("submit", function () {
            sessionStorage.setItem(SESSION_KEY, "1");
        });
    }

    function maybeReopenDrawer() {
        if (sessionStorage.getItem(SESSION_KEY) !== "1") {
            return;
        }
        sessionStorage.removeItem(SESSION_KEY);
        // Wait for Alpine.js to hydrate the container before triggering the click.
        setTimeout(openDrawer, 60);
    }

    ready(function () {
        hideDefaultFilterTriggers();
        bindAutoSubmit();
        maybeReopenDrawer();
    });
})();
