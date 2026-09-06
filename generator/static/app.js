/* Avatar fallback. A student's avatar URL can 404 or refuse hotlinking, and an
 * empty circle looks broken. Swap a failed image for the initials monogram.
 * Runs on every page, including bio pages that have no filter controls.
 */
(function () {
  "use strict";

  function monogram(img) {
    var span = document.createElement("span");
    var size = img.className.match(/avatar--(?:sm|xl)\b/);
    span.className = "avatar avatar--mono" + (size ? " " + size[0] : "");
    span.setAttribute("aria-hidden", "true");
    span.textContent = img.getAttribute("data-initials") || "?";
    img.replaceWith(span);
  }

  Array.prototype.forEach.call(document.querySelectorAll("img[data-initials]"), function (img) {
    if (img.complete && img.naturalWidth === 0) {
      monogram(img);
      return;
    }
    img.addEventListener("error", function () {
      monogram(img);
    }, { once: true });
  });
})();

/* Client-side search + team filtering for the bio wall.
 * Vanilla, no dependencies, no globals: everything lives in this IIFE.
 * The markup is fully readable with JS disabled; these controls are
 * hidden by CSS until the `js` class lands on <html>.
 */
(function () {
  "use strict";

  var controls = document.querySelector("[data-controls]");
  if (!controls) {
    return;
  }

  var input = document.querySelector("[data-search-input]");
  var resetButton = document.querySelector("[data-reset]");
  var resultsEl = document.querySelector("[data-results]");
  var noResultsEl = document.querySelector("[data-no-results]");
  var chips = Array.prototype.slice.call(document.querySelectorAll("[data-team-filter]"));
  var sections = Array.prototype.slice.call(document.querySelectorAll("[data-team-section]"));

  var cards = Array.prototype.slice.call(document.querySelectorAll("[data-card]")).map(function (el) {
    return {
      el: el,
      team: el.getAttribute("data-team") || "",
      haystack: (el.getAttribute("data-search") || "").toLowerCase().replace(/\s+/g, " ")
    };
  });

  if (!cards.length) {
    return;
  }

  var total = cards.length;
  var activeTeams = new Set();
  var terms = [];

  function parse(value) {
    return value
      .toLowerCase()
      .split(/\s+/)
      .filter(function (term) {
        return term.length > 0;
      });
  }

  function matches(card) {
    if (activeTeams.size > 0 && !activeTeams.has(card.team)) {
      return false;
    }
    for (var i = 0; i < terms.length; i += 1) {
      if (card.haystack.indexOf(terms[i]) === -1) {
        return false;
      }
    }
    return true;
  }

  function apply() {
    var visible = 0;
    var perTeam = Object.create(null);

    cards.forEach(function (card) {
      var show = matches(card);
      card.el.hidden = !show;
      if (show) {
        visible += 1;
        perTeam[card.team] = (perTeam[card.team] || 0) + 1;
      }
    });

    var filtering = terms.length > 0 || activeTeams.size > 0;

    sections.forEach(function (section) {
      var slug = section.getAttribute("data-team-section");
      var count = perTeam[slug] || 0;
      // While filtering, a team with no visible cards disappears entirely.
      // Unfiltered, empty teams stay put so the class can watch them fill up.
      section.hidden = filtering && count === 0;
    });

    if (noResultsEl) {
      noResultsEl.hidden = visible !== 0;
    }

    if (resetButton) {
      resetButton.hidden = !filtering;
    }

    if (resultsEl) {
      resultsEl.textContent =
        visible === total
          ? "Showing all " + total + (total === 1 ? " bio" : " bios")
          : "Showing " + visible + " of " + total + " bios";
    }
  }

  var timer = 0;
  function scheduleApply() {
    window.clearTimeout(timer);
    timer = window.setTimeout(apply, 140);
  }

  if (input) {
    input.addEventListener("input", function () {
      terms = parse(input.value);
      scheduleApply();
    });

    input.addEventListener("keydown", function (event) {
      if (event.key === "Escape" && input.value !== "") {
        input.value = "";
        terms = [];
        apply();
      }
    });
  }

  chips.forEach(function (chip) {
    chip.addEventListener("click", function () {
      var slug = chip.getAttribute("data-team-filter");
      var pressed = chip.getAttribute("aria-pressed") === "true";
      if (pressed) {
        activeTeams.delete(slug);
      } else {
        activeTeams.add(slug);
      }
      chip.setAttribute("aria-pressed", pressed ? "false" : "true");
      apply();
    });
  });

  if (resetButton) {
    resetButton.addEventListener("click", function () {
      activeTeams.clear();
      terms = [];
      if (input) {
        input.value = "";
      }
      chips.forEach(function (chip) {
        chip.setAttribute("aria-pressed", "false");
      });
      apply();
      if (input) {
        input.focus();
      }
    });
  }

  apply();
})();
