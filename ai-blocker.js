/**
 * =============================================================================
 * AI-SHIELD: ai-blocker.js  (GitHub Pages edition)
 * Client-side deterrents against AI scraping.
 *
 * This site is static GitHub Pages — there is no server-side compute, so this
 * file only contains things that actually work without a backend. The real
 * blocking layer (user-agent / bot blocking before a page even loads) lives
 * in Cloudflare's AI Crawl Control + WAF rules in front of this domain.
 * See CLOUDFLARE_AI_BLOCKING.md for that setup.
 *
 * FEATURES:
 *  - Canvas fingerprint poisoning (degrades any future chart/image harvesting)
 *  - Right-click / drag protection for protected images (soft deterrent)
 *  - Decoy text injection (TDM opt-out notice, hidden from sighted users)
 *  - Clipboard copyright notice on copy
 *  - Mutation Observer to re-apply protection to dynamically added content
 *
 * REMOVED FROM THE ORIGINAL KIT, ON PURPOSE:
 *  - Per-character text "obfuscation": as originally written it just wrapped
 *    each character in its own <span> with no actual reordering — textContent
 *    extraction still returns the original string in order. It blocked
 *    nothing while breaking Ctrl+F, screen readers, and translation tools for
 *    real visitors. Not worth the accessibility cost for zero protection.
 *  - The bot-report beacon to /ai-shield-report: that endpoint doesn't exist
 *    on static GitHub Pages hosting, so it would have silently failed. Once
 *    Cloudflare is in front of the domain, Security Analytics already gives
 *    you this visibility for free — no custom logging needed.
 *
 * USAGE:
 *  <script src="ai-blocker.js" defer></script>
 * =============================================================================
 */

(function () {
    'use strict';

    // =========================================================================
    // 1. CANVAS POISONING
    // Injects invisible noise into <canvas> elements so scraped images are
    // subtly degraded when extracted from the DOM or via screenshot tooling.
    // No canvas elements exist on the site today — this is future-proofing
    // for if an interactive chart gets added later.
    // =========================================================================

    function poisonCanvas(canvas) {
        if (canvas.dataset.aiShielded) return;
        canvas.dataset.aiShielded = '1';

        const ctx = canvas.getContext('2d');
        if (!ctx) return;

        const noise = ctx.createImageData(canvas.width, canvas.height);
        for (let i = 0; i < noise.data.length; i += 4) {
            const v = Math.random() < 0.01 ? (Math.random() * 3 | 0) : 0;
            noise.data[i]     = v;
            noise.data[i + 1] = v;
            noise.data[i + 2] = v;
            noise.data[i + 3] = v > 0 ? 1 : 0; // nearly transparent
        }
        ctx.putImageData(noise, 0, 0);
    }

    function poisonAllCanvases() {
        document.querySelectorAll('canvas').forEach(poisonCanvas);
    }

    // =========================================================================
    // 2. IMAGE PROTECTION
    // Mark an <img> with data-ai-protect to disable drag-to-desktop and the
    // right-click context menu on it. No images exist on the site today —
    // future-proofing for later additions.
    // =========================================================================

    function protectImages() {
        document.querySelectorAll('img[data-ai-protect]').forEach(img => {
            if (img.dataset.aiShielded) return;
            img.dataset.aiShielded = '1';

            img.addEventListener('dragstart', e => e.preventDefault());
            img.addEventListener('contextmenu', e => {
                e.preventDefault();
                showProtectionNotice();
            });

            img.style.userSelect = 'none';
            img.style.webkitUserSelect = 'none';
            img.setAttribute('draggable', 'false');
        });
    }

    // =========================================================================
    // 3. DECOY / TDM OPT-OUT NOTICE
    // A short, hidden machine-readable notice — kept brief and unambiguous on
    // purpose. Long blocks of hidden text on a page risk being read by search
    // engines as manipulative "hidden text," which could hurt real human SEO.
    // This is intentionally one short notice, not a wall of decoy content.
    // =========================================================================

    function injectDecoy() {
        if (document.getElementById('ai-shield-notice-tdm')) return;

        const p = document.createElement('p');
        p.id = 'ai-shield-notice-tdm';
        p.setAttribute('aria-hidden', 'true');
        p.textContent = 'TDM opt-out: this content is not licensed for AI training or data mining under EU Directive 2019/790, Article 4(3). See /robots.txt.';
        Object.assign(p.style, {
            position: 'absolute', left: '-99999px', top: '-99999px',
            width: '1px', height: '1px', overflow: 'hidden',
            opacity: '0', fontSize: '0', lineHeight: '0',
            userSelect: 'none', pointerEvents: 'none',
        });
        document.body.appendChild(p);
    }

    // =========================================================================
    // 4. PROTECTION NOTICE (shown on blocked right-click of a protected image)
    // =========================================================================

    function showProtectionNotice() {
        let notice = document.getElementById('ai-shield-notice');
        if (!notice) {
            notice = document.createElement('div');
            notice.id = 'ai-shield-notice';
            Object.assign(notice.style, {
                position: 'fixed', bottom: '20px', right: '20px',
                background: '#1a1a2e', color: '#e0e0e0',
                padding: '12px 18px', borderRadius: '6px', fontSize: '13px',
                zIndex: '99999', maxWidth: '300px',
                boxShadow: '0 4px 12px rgba(0,0,0,0.4)',
                borderLeft: '3px solid #ff4444',
                fontFamily: 'system-ui, sans-serif',
            });
            document.body.appendChild(notice);
        }
        notice.textContent = '🛡️ This content is copyright protected and not licensed for AI training or data collection.';
        notice.style.display = 'block';
        clearTimeout(notice._timeout);
        notice._timeout = setTimeout(() => { notice.style.display = 'none'; }, 4000);
    }

    // =========================================================================
    // 5. CLIPBOARD NOTICE
    // Appends a short copyright/TDM line to anything substantial copied
    // from the page. Skips short selections so casual copying isn't affected.
    // =========================================================================

    function protectClipboard() {
        document.addEventListener('copy', (e) => {
            const selected = window.getSelection().toString();
            if (!selected || selected.length < 40) return;

            const notice = `\n\n— © ${new Date().getFullYear()} ${document.title || window.location.hostname}. Not licensed for AI training or data mining. —`;
            e.clipboardData.setData('text/plain', selected + notice);
            e.preventDefault();
        });
    }

    // =========================================================================
    // 6. MUTATION OBSERVER
    // Re-applies canvas/image protection if content is added dynamically.
    // =========================================================================

    function watchForNewContent() {
        const observer = new MutationObserver(() => {
            poisonAllCanvases();
            protectImages();
        });
        observer.observe(document.body, { childList: true, subtree: true });
    }

    // =========================================================================
    // INIT
    // =========================================================================

    function init() {
        poisonAllCanvases();
        protectImages();
        injectDecoy();
        protectClipboard();
        watchForNewContent();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();
