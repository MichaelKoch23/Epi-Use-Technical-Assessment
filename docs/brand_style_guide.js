/* =========================================================================
   Employee Hierarchy Management System — Brand Style Guide behaviour
   Contrast maths and scrollspy carried over unchanged; the interactive
   demos below are specific to the hierarchy components.
   ========================================================================= */

if (typeof lucide !== "undefined") lucide.createIcons();

/* ------------------------------------------------- WCAG contrast ratios */

function _wcagLin(c) {
	c /= 255;
	return c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
}

function _wcagLum(color) {
	color = color.trim();
	let r, g, b;
	const rgb = color.match(/rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)/);
	if (rgb) {
		r = Number.parseInt(rgb[1]);
		g = Number.parseInt(rgb[2]);
		b = Number.parseInt(rgb[3]);
	} else {
		const hex = color.replace(/^#/, "");
		const h =
			hex.length === 3
				? hex
						.split("")
						.map(function (c) {
							return c + c;
						})
						.join("")
				: hex;
		r = Number.parseInt(h.slice(0, 2), 16);
		g = Number.parseInt(h.slice(2, 4), 16);
		b = Number.parseInt(h.slice(4, 6), 16);
	}
	return 0.2126 * _wcagLin(r) + 0.7152 * _wcagLin(g) + 0.0722 * _wcagLin(b);
}

function _wcagContrast(a, b) {
	let L1 = _wcagLum(a);
	let L2 = _wcagLum(b);
	if (L1 < L2) {
		const t = L1;
		L1 = L2;
		L2 = t;
	}
	return (L1 + 0.05) / (L2 + 0.05);
}

const _cs = getComputedStyle(document.documentElement);

document.querySelectorAll(".auto-ratio").forEach(function (span) {
	const fg = _cs.getPropertyValue(span.dataset.fg).trim();
	const bg = _cs.getPropertyValue(span.dataset.bg).trim();
	if (!fg || !bg) return;
	const ratio = _wcagContrast(fg, bg);
	span.dataset.ratio = ratio;
	span.textContent = (Math.floor(ratio * 10) / 10).toFixed(1) + ":1";
});

document.querySelectorAll(".contrast-table tbody tr").forEach(function (row) {
	const ratioSpan = row.querySelector(".auto-ratio");
	if (!ratioSpan) return;
	const r = Number.parseFloat(ratioSpan.dataset.ratio);
	if (Number.isNaN(r)) return;
	let badge;
	if (r >= 7) badge = '<span class="pass-badge">AAA</span>';
	else if (r >= 4.5) badge = '<span class="pass-badge">AA</span>';
	else if (r >= 3) badge = '<span class="warn-badge">Large text only</span>';
	else badge = '<span class="warn-badge">Decorative only</span>';
	row.cells[row.cells.length - 1].innerHTML = badge;
});

/* --------------------------------------------------------- nav scrollspy */

const navLinks = document.querySelectorAll(".site-nav a");

const observer = new IntersectionObserver(
	(entries) => {
		entries.forEach((entry) => {
			if (!entry.isIntersecting) return;
			navLinks.forEach((a) => a.classList.remove("active"));
			const active = document.querySelector(
				`.site-nav a[href="#${entry.target.id}"]`,
			);
			if (active) active.classList.add("active");
		});
	},
	{ rootMargin: "-30% 0px -60% 0px" },
);

document.querySelectorAll("section[id]").forEach((s) => observer.observe(s));

/* ------------------------------------------------------- copy hex values */

document.querySelectorAll(".colour-role-card[data-hex]").forEach((card) => {
	card.querySelector(".colour-swatch").style.background =
		card.dataset.bg || card.dataset.hex;
	card.setAttribute("tabindex", "0");
	card.setAttribute("role", "button");

	function copyHex() {
		if (!navigator.clipboard) return;
		navigator.clipboard
			.writeText(card.dataset.hex)
			.then(() => {
				const hint = card.querySelector(".colour-copy-hint");
				hint.textContent = "Copied";
				hint.style.opacity = "1";
				setTimeout(() => {
					hint.textContent = "Copy hex";
					hint.style.opacity = "";
				}, 1500);
			})
			.catch(() => {});
	}

	card.addEventListener("click", copyHex);
	card.addEventListener("keydown", (e) => {
		if (e.key === "Enter" || e.key === " ") {
			e.preventDefault();
			copyHex();
		}
	});
});

/* ----------------------------------------------------------- motion demo */

document.querySelectorAll(".motion-card[data-dur]").forEach((card) => {
	const dot = card.querySelector(".motion-dot");
	const track = card.querySelector(".motion-track");
	if (!dot || !track) return;

	const dur = _cs.getPropertyValue(card.dataset.dur).trim();
	const ease = _cs.getPropertyValue(card.dataset.ease || "--ease-standard").trim();
	dot.style.transition = `transform ${dur} ${ease}`;

	let out = false;
	function toggle() {
		out = !out;
		dot.style.transform = out
			? `translateX(${track.clientWidth - 24}px)`
			: "translateX(0)";
	}

	card.addEventListener("click", toggle);
	card.setAttribute("tabindex", "0");
	card.setAttribute("role", "button");
	card.addEventListener("keydown", (e) => {
		if (e.key === "Enter" || e.key === " ") {
			e.preventDefault();
			toggle();
		}
	});
});

/* ------------------------------------------- drag-to-reassign demo states */

/* The live application computes valid drop targets from the loaded subtree.
   Here the descendant set is hardcoded purely to demonstrate the visual
   states: a node may never be dropped onto one of its own descendants. */

const dragDemo = document.querySelector("[data-drag-demo]");

if (dragDemo) {
	const source = dragDemo.querySelector("[data-drag-source]");
	const targets = dragDemo.querySelectorAll("[data-drop-target]");

	function clearStates() {
		source.classList.remove("is-dragging");
		targets.forEach((t) =>
			t.classList.remove("is-drop-valid", "is-drop-invalid"),
		);
	}

	function showStates() {
		source.classList.add("is-dragging");
		targets.forEach((t) => {
			const valid = t.dataset.dropTarget === "valid";
			t.classList.add(valid ? "is-drop-valid" : "is-drop-invalid");
		});
	}

	let active = false;
	dragDemo
		.querySelector("[data-drag-toggle]")
		?.addEventListener("click", function () {
			active = !active;
			this.textContent = active ? "Reset demo" : "Simulate drag";
			if (active) showStates();
			else clearStates();
		});
}

/* -------------------------------------------------- collapse / expand node */

document.querySelectorAll(".node-collapse").forEach((btn) => {
	btn.addEventListener("click", () => {
		const expanded = btn.getAttribute("aria-expanded") === "true";
		btn.setAttribute("aria-expanded", String(!expanded));
		btn.textContent = expanded ? "+" : "−";
		const branch = document.getElementById(btn.getAttribute("aria-controls"));
		if (branch) branch.hidden = expanded;
	});
});

/* ------------------------------------------------- deletion policy picker */

document.querySelectorAll("[data-policy-group]").forEach((group) => {
	const options = group.querySelectorAll(".policy-option");
	options.forEach((option) => {
		option.addEventListener("click", () => {
			options.forEach((o) => o.classList.remove("is-selected"));
			option.classList.add("is-selected");
			option.querySelector("input")?.click();
		});
	});
});

/* ------------------------------------------------------ small demo bits */

document.querySelectorAll(".filter-chip-remove").forEach((btn) => {
	btn.addEventListener("click", () => btn.closest(".filter-chip")?.remove());
});

document.querySelectorAll(".search-clear-btn").forEach((btn) => {
	btn.addEventListener("click", () => {
		const input = btn.parentElement?.querySelector(".search-input");
		if (input) {
			input.value = "";
			input.focus();
		}
	});
});

document.querySelectorAll(".toast-close").forEach((btn) => {
	btn.addEventListener("click", () => btn.closest(".toast")?.remove());
});