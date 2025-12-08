document.addEventListener('DOMContentLoaded', () => {
    const bootSequence = document.getElementById('boot-sequence');
    const dashboard = document.getElementById('dashboard');
    const timeDisplay = document.getElementById('current-time');
    const cmdInput = document.getElementById('cmd-input');
    const themeToggle = document.getElementById('theme-toggle');

    // 0. Theme Toggle
    themeToggle.addEventListener('click', () => {
        const body = document.body;
        if (body.getAttribute('data-theme') === 'light') {
            body.removeAttribute('data-theme');
            themeToggle.textContent = '[ LIGHT MODE ]';
        } else {
            body.setAttribute('data-theme', 'light');
            themeToggle.textContent = '[ DARK MODE ]';
        }
    });

    // 1. Clock Update
    function updateTime() {
        const now = new Date();
        timeDisplay.textContent = now.toISOString().replace('T', ' ').substring(0, 19) + ' UTC';
    }
    setInterval(updateTime, 1000);
    updateTime();

    // 2. Boot Sequence Simulation
    const logs = [
        "> INITIALIZING REGIME ANALYZER...",
        "> CONNECTING TO DATA STREAMS...",
        "> FETCHING BTC PRICE ACTION... [OK]",
        "> ANALYZING FED HAWKISHNESS... [OK]",
        "> SCANNING 20,000+ HISTORICAL PATTERNS...",
        "> CALCULATING COSINE SIMILARITY...",
        "> MATCH FOUND: 2022-03-15 (SCORE: 0.87)",
        "> GENERATING REPORT UI..."
    ];

    let delay = 0;
    logs.forEach((log, index) => {
        setTimeout(() => {
            const p = document.createElement('div');
            p.className = 'log-line';
            p.textContent = log;
            bootSequence.appendChild(p);

            // Scroll to bottom
            bootSequence.scrollTop = bootSequence.scrollHeight;

            // Finish boot
            if (index === logs.length - 1) {
                setTimeout(() => {
                    bootSequence.classList.add('hidden');
                    dashboard.classList.remove('hidden');
                    cmdInput.focus();
                }, 800);
            }
        }, delay);
        delay += Math.random() * 300 + 100; // Random delay between 100-400ms
    });

    // 3. Command Line Handling
    cmdInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            const cmd = cmdInput.value.trim().toLowerCase();
            handleCommand(cmd);
            cmdInput.value = '';
        }
    });

    function handleCommand(cmd) {
        // Simple mock responses for prototype
        if (cmd === '/help') {
            alert("COMMANDS:\n/today - Show today's report\n/match - Show historical twins\n/btc - BTC specific analysis\n/fed - Fed stance tracker");
        } else if (cmd === '/today') {
            location.reload(); // Reset view
        } else if (cmd === '/btc') {
            alert("BTC REGIME: Institutional Accumulation. Price holding above $90k support.");
        } else {
            // Simulate error
            const originalPlaceholder = cmdInput.placeholder;
            cmdInput.placeholder = `ERROR: Unknown command '${cmd}'`;
            cmdInput.classList.add('text-red');
            setTimeout(() => {
                cmdInput.placeholder = originalPlaceholder;
                cmdInput.classList.remove('text-red');
            }, 2000);
        }
    }
});
