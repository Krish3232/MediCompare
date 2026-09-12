/* =========================================================
   MEDICOMPARE — ADVANCED CLIENT JAVASCRIPT
   Micro-interactions, GPS Geolocation, and Real-time Helpers
   ========================================================= */

document.addEventListener("DOMContentLoaded", function () {

    console.log("MediCompare 2.0 Client Engine Initialized.");

    /* =====================================================
       1. STICKY HEADER SCROLL EFFECT
    ====================================================== */
    const header = document.getElementById("siteHeader");
    if (header) {
        window.addEventListener("scroll", () => {
            if (window.scrollY > 20) {
                header.classList.add("scrolled");
            } else {
                header.classList.remove("scrolled");
            }
        });
    }


    /* =====================================================
       2. MOBILE NAVIGATION DRAWER
    ====================================================== */
    const mobileToggle = document.getElementById("mobileNavToggle");
    const mainNav = document.getElementById("mainNav");

    if (mobileToggle && mainNav) {
        mobileToggle.addEventListener("click", () => {
            const isOpen = mainNav.classList.toggle("open");
            mobileToggle.setAttribute("aria-expanded", isOpen ? "true" : "false");
        });

        // Close when clicking outside
        document.addEventListener("click", (e) => {
            if (!mobileToggle.contains(e.target) && !mainNav.contains(e.target)) {
                mainNav.classList.remove("open");
                mobileToggle.setAttribute("aria-expanded", "false");
            }
        });
    }


    /* =====================================================
       3. AUTO-DISMISS FLASH NOTIFICATIONS
    ====================================================== */
    const flashItems = document.querySelectorAll(".flash");
    flashItems.forEach((flash) => {
        const closeBtn = flash.querySelector(".flash-close");
        if (closeBtn) {
            closeBtn.addEventListener("click", () => {
                flash.style.opacity = "0";
                flash.style.transform = "translateY(-10px)";
                flash.style.transition = "all 0.3s ease";
                setTimeout(() => flash.remove(), 300);
            });
        }

        // Auto dismiss after 6 seconds
        setTimeout(() => {
            if (flash && flash.parentElement) {
                flash.style.opacity = "0";
                flash.style.transform = "translateY(-10px)";
                flash.style.transition = "all 0.4s ease";
                setTimeout(() => flash.remove(), 400);
            }
        }, 6000);
    });


    /* =====================================================
       4. ANIMATED NUMERIC COUNTERS
    ====================================================== */
    const statCounters = document.querySelectorAll(".hero-stat-card strong, .hd-stat strong, .admin-stat-card strong");
    
    if ("IntersectionObserver" in window) {
        const observer = new IntersectionObserver((entries, obs) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const el = entry.target;
                    const text = el.textContent.trim();
                    const match = text.match(/^(\d+)/);
                    if (match) {
                        const target = parseInt(match[1], 10);
                        const suffix = text.replace(/^\d+/, '');
                        let current = 0;
                        const duration = 1200;
                        const stepTime = Math.max(Math.floor(duration / (target || 1)), 20);
                        
                        const timer = setInterval(() => {
                            current += Math.ceil(target / 30);
                            if (current >= target) {
                                el.textContent = target + suffix;
                                clearInterval(timer);
                            } else {
                                el.textContent = current + suffix;
                            }
                        }, stepTime);
                    }
                    obs.unobserve(el);
                }
            });
        }, { threshold: 0.2 });

        statCounters.forEach(counter => observer.observe(counter));
    }


    /* =====================================================
       5. STAR RATING SELECTOR HELPER
    ====================================================== */
    const ratingSelect = document.getElementById("rating");
    if (ratingSelect && ratingSelect.tagName === "SELECT") {
        ratingSelect.addEventListener("change", function () {
            this.style.borderColor = "var(--primary)";
        });
    }

});


/* =========================================================
   6. GPS GEOLOCATION & GOOGLE MAPS DIRECTIONS
========================================================= */

function getDirections(address, city) {
    if (!address && !city) {
        alert("Hospital address information is not available.");
        return;
    }

    const destination = encodeURIComponent(((address || '') + ", " + (city || '')).trim());

    if (!navigator.geolocation) {
        // Direct fallback to Google Maps without origin
        const fallbackUrl = `https://www.google.com/maps/search/?api=1&query=${destination}`;
        window.open(fallbackUrl, "_blank");
        return;
    }

    // Show temporary feedback
    console.log("Requesting GPS coordinates for route navigation...");

    navigator.geolocation.getCurrentPosition(
        function (position) {
            const latitude = position.coords.latitude;
            const longitude = position.coords.longitude;
            const mapsUrl = `https://www.google.com/maps/dir/?api=1&origin=${latitude},${longitude}&destination=${destination}&travelmode=driving`;
            window.open(mapsUrl, "_blank");
        },
        function (error) {
            console.warn("Geolocation warning:", error.message);
            // Graceful fallback to search query on maps
            const fallbackUrl = `https://www.google.com/maps/search/?api=1&query=${destination}`;
            window.open(fallbackUrl, "_blank");
        },
        {
            enableHighAccuracy: true,
            timeout: 8000,
            maximumAge: 0
        }
    );
}

function openAddressDirections(destination) {
    const encoded = encodeURIComponent(destination);
    const mapsUrl = `https://www.google.com/maps/dir/?api=1&destination=${encoded}&travelmode=driving`;
    window.open(mapsUrl, "_blank");
}