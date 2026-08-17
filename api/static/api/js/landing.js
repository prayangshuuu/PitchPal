document.addEventListener('DOMContentLoaded', () => {
    // ---- Mobile hamburger menu ----
    const menuButton = document.getElementById('mobile-menu-button');
    const mobileMenu = document.getElementById('mobile-menu');
    const iconOpen = document.getElementById('menu-icon-open');
    const iconClose = document.getElementById('menu-icon-close');

    if (menuButton && mobileMenu) {
        menuButton.addEventListener('click', () => {
            const isOpen = !mobileMenu.classList.contains('hidden');
            mobileMenu.classList.toggle('hidden');
            iconOpen.classList.toggle('hidden');
            iconClose.classList.toggle('hidden');
            menuButton.setAttribute('aria-expanded', String(!isOpen));
        });
    }

    // ---- Smooth scroll for in-page nav links ----
    document.querySelectorAll('.nav-scroll-link').forEach((link) => {
        link.addEventListener('click', (event) => {
            const href = link.getAttribute('href');
            if (!href || !href.startsWith('#')) return;
            const target = document.querySelector(href);
            if (!target) return;
            event.preventDefault();
            target.scrollIntoView({ behavior: 'smooth', block: 'start' });

            if (mobileMenu && !mobileMenu.classList.contains('hidden')) {
                mobileMenu.classList.add('hidden');
                iconOpen.classList.remove('hidden');
                iconClose.classList.add('hidden');
                menuButton.setAttribute('aria-expanded', 'false');
            }
        });
    });

    // ---- FAQ accordion ----
    document.querySelectorAll('.faq-trigger').forEach((trigger) => {
        trigger.addEventListener('click', () => {
            const item = trigger.closest('.faq-item');
            const panel = item.querySelector('.faq-panel');
            const icon = trigger.querySelector('.faq-icon');
            const isOpen = trigger.getAttribute('aria-expanded') === 'true';

            document.querySelectorAll('.faq-trigger').forEach((otherTrigger) => {
                if (otherTrigger === trigger) return;
                otherTrigger.setAttribute('aria-expanded', 'false');
                otherTrigger.closest('.faq-item').querySelector('.faq-panel').classList.add('hidden');
                otherTrigger.querySelector('.faq-icon').classList.remove('rotate-180');
            });

            trigger.setAttribute('aria-expanded', String(!isOpen));
            panel.classList.toggle('hidden', isOpen);
            icon.classList.toggle('rotate-180', !isOpen);
        });
    });

    // ---- Scroll reveal animations ----
    const revealEls = document.querySelectorAll('.reveal');
    if ('IntersectionObserver' in window && revealEls.length) {
        const observer = new IntersectionObserver((entries) => {
            entries.forEach((entry) => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('revealed');
                    observer.unobserve(entry.target);
                }
            });
        }, { threshold: 0.15, rootMargin: '0px 0px -40px 0px' });

        revealEls.forEach((el) => observer.observe(el));
    } else {
        revealEls.forEach((el) => el.classList.add('revealed'));
    }

    // ---- Counter animation ----
    document.querySelectorAll('.counter').forEach((counterEl) => {
        const target = parseInt(counterEl.getAttribute('data-target'), 10) || 0;
        const suffix = counterEl.getAttribute('data-suffix') || '';
        const duration = 1500;
        let started = false;

        const animate = () => {
            if (started) return;
            started = true;
            const startTime = performance.now();
            const step = (now) => {
                const progress = Math.min((now - startTime) / duration, 1);
                const eased = 1 - Math.pow(1 - progress, 3);
                const value = Math.floor(eased * target);
                counterEl.textContent = value.toLocaleString() + suffix;
                if (progress < 1) requestAnimationFrame(step);
            };
            requestAnimationFrame(step);
        };

        if ('IntersectionObserver' in window) {
            const counterObserver = new IntersectionObserver((entries) => {
                entries.forEach((entry) => {
                    if (entry.isIntersecting) {
                        animate();
                        counterObserver.unobserve(entry.target);
                    }
                });
            }, { threshold: 0.5 });
            counterObserver.observe(counterEl);
        } else {
            animate();
        }
    });

    // ---- Button ripple effect ----
    document.querySelectorAll('.btn-ripple').forEach((button) => {
        button.addEventListener('click', function (event) {
            const rect = button.getBoundingClientRect();
            const ripple = document.createElement('span');
            const size = Math.max(rect.width, rect.height);
            ripple.style.position = 'absolute';
            ripple.style.width = ripple.style.height = `${size}px`;
            ripple.style.left = `${event.clientX - rect.left - size / 2}px`;
            ripple.style.top = `${event.clientY - rect.top - size / 2}px`;
            ripple.style.borderRadius = '50%';
            ripple.style.background = 'rgba(255,255,255,0.5)';
            ripple.style.transform = 'scale(0)';
            ripple.style.pointerEvents = 'none';
            ripple.style.transition = 'transform 0.6s ease-out, opacity 0.6s ease-out';
            button.appendChild(ripple);

            requestAnimationFrame(() => {
                ripple.style.transform = 'scale(1.5)';
                ripple.style.opacity = '0';
            });

            setTimeout(() => ripple.remove(), 650);
        });
    });
});
