document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('bot-form');
    const startBtn = document.getElementById('start-btn');
    const stopBtn = document.getElementById('stop-btn');
    const terminal = document.getElementById('terminal');
    const statusInd = document.getElementById('status-ind');
    
    let pollInterval = null;

    function log(msg, type='info') {
        const div = document.createElement('div');
        div.className = `line ${type}`;
        div.textContent = msg;
        terminal.appendChild(div);
        terminal.scrollTop = terminal.scrollHeight;
    }

    async function updateStatus() {
        try {
            const res = await fetch('/api/status');
            const data = await res.json();
            
            // Update UI State
            if (data.running) {
                statusInd.textContent = "RUNNING";
                statusInd.classList.add('running');
                startBtn.disabled = true;
                stopBtn.disabled = false;
                form.querySelectorAll('input').forEach(i => i.disabled = true);
            } else {
                statusInd.textContent = "STOPPED";
                statusInd.classList.remove('running');
                startBtn.disabled = false;
                stopBtn.disabled = true;
                form.querySelectorAll('input').forEach(i => i.disabled = false);
            }

            // Update Logs
            // We clear and redraw or append? 
            // Simple: Clear and redraw for sync
            terminal.innerHTML = '';
            if (data.logs.length === 0) {
                 log("Waiting for logs...", "system");
            } else {
                data.logs.forEach(l => {
                    const type = l.toLowerCase().includes('error') ? 'error' : 'info';
                    log(l, type);
                });
            }
            
        } catch (e) {
            console.error(e);
            statusInd.textContent = "DISCONNECTED";
        }
    }

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const payload = {
            target: document.getElementById('target').value,
            amount: document.getElementById('amount').value,
            private_key: document.getElementById('pk').value,
            api_key: document.getElementById('api_key').value,
            api_secret: document.getElementById('api_secret').value,
            passphrase: document.getElementById('passphrase').value,
        };

        startBtn.textContent = "Starting...";
        startBtn.disabled = true;

        try {
            const res = await fetch('/api/start', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const data = await res.json();
            
            if (res.ok) {
                log("Bot start signal sent.", "system");
                updateStatus();
            } else {
                log(`Error: ${data.message}`, "error");
                startBtn.disabled = false;
                startBtn.textContent = "Start Bot";
            }
        } catch (err) {
            log(`Request failed: ${err}`, "error");
            startBtn.disabled = false;
        }
    });

    stopBtn.addEventListener('click', async () => {
        stopBtn.disabled = true;
        stopBtn.textContent = "Stopping...";
        await fetch('/api/stop', { method: 'POST' });
        log("Bot stop signal sent.", "system");
        setTimeout(updateStatus, 1000);
    });

    // Initial Poll
    updateStatus();
    pollInterval = setInterval(updateStatus, 2000);
});
