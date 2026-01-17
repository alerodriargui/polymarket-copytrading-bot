document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('bot-form');
    const startBtn = document.getElementById('start-btn');
    const stopBtn = document.getElementById('stop-btn');
    const terminal = document.getElementById('terminal');
    const statusInd = document.getElementById('status-ind');
    const matchAmountParams = document.getElementById('match_amount');
    const amountInput = document.getElementById('amount');
    
    let pollInterval = null;

    function addLog(msg, type='info') {
        const entry = document.createElement('div');
        entry.className = `log-entry ${type}`;
        
        const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false });
        
        entry.innerHTML = `
            <span class="log-time">${time}</span>
            <span class="log-msg">${msg}</span>
        `;
        
        terminal.appendChild(entry);
        terminal.scrollTop = terminal.scrollHeight;
    }

    async function updateStatus() {
        try {
            const res = await fetch('/api/status');
            const data = await res.json();
            
            // Update UI State
            if (data.running) {
                statusInd.querySelector('span').textContent = "RUNNING";
                statusInd.classList.add('running');
                startBtn.disabled = true;
                stopBtn.disabled = false;
                form.querySelectorAll('input').forEach(i => i.disabled = true);
            } else {
                statusInd.querySelector('span').textContent = "OFFLINE";
                statusInd.classList.remove('running');
                startBtn.disabled = false;
                stopBtn.disabled = true;
                form.querySelectorAll('input').forEach(i => {
                    // Re-enable inputs but respect match_amount toggle
                    if (i.id === 'amount' && matchAmountParams.checked) {
                        i.disabled = true;
                    } else {
                        i.disabled = false;
                    }
                });
            }

            // Update Logs
            // Avoid flickering: only clear if content is different
            if (data.logs.length > 0) {
                const currentLogCount = terminal.querySelectorAll('.log-entry').length;
                if (data.logs.length !== currentLogCount) {
                    terminal.innerHTML = '';
                    data.logs.slice().reverse().forEach(l => {
                        let type = 'info';
                        if (l.toLowerCase().includes('error')) type = 'error';
                        if (l.toLowerCase().includes('executed')) type = 'success';
                        if (l.toLowerCase().includes('system')) type = 'system';
                        
                        // Parse existing time from log string if possible
                        // Log format: "HH:MM:SS - Message"
                        const match = l.match(/^(\d{2}:\d{2}:\d{2}) - (.*)$/);
                        if (match) {
                            const entry = document.createElement('div');
                            entry.className = `log-entry ${type}`;
                            entry.innerHTML = `<span class="log-time">${match[1]}</span><span class="log-msg">${match[2]}</span>`;
                            terminal.appendChild(entry);
                        } else {
                            addLog(l, type);
                        }
                    });
                    terminal.scrollTop = terminal.scrollHeight;
                }
            } else if (terminal.children.length === 0) {
                addLog("Waiting for activity...", "system");
            }
            
        } catch (e) {
            console.error("Status check failed", e);
            statusInd.querySelector('span').textContent = "DISCONNECTED";
            statusInd.classList.remove('running');
        }
    }

    matchAmountParams.addEventListener('change', (e) => {
        if (e.target.checked) {
            amountInput.disabled = true;
            amountInput.value = "";
            amountInput.placeholder = "Dynamic Size";
        } else {
            amountInput.disabled = false;
            amountInput.value = "10";
            amountInput.placeholder = "";
        }
    });

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const payload = {
            target: document.getElementById('target').value,
            amount: document.getElementById('amount').value,
            match_amount: document.getElementById('match_amount').checked,
            private_key: document.getElementById('pk').value,
            api_key: document.getElementById('api_key').value,
            api_secret: document.getElementById('api_secret').value,
            passphrase: document.getElementById('passphrase').value,
        };

        const originalText = startBtn.innerHTML;
        startBtn.innerHTML = '<span class="loading">Initializing...</span>';
        startBtn.disabled = true;

        try {
            const res = await fetch('/api/start', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const data = await res.json();
            
            if (res.ok) {
                addLog("Replication engine started successfully.", "success");
                updateStatus();
            } else {
                addLog(`Startup Error: ${data.message}`, "error");
                startBtn.innerHTML = originalText;
                startBtn.disabled = false;
            }
        } catch (err) {
            addLog(`Network Failure: ${err}`, "error");
            startBtn.innerHTML = originalText;
            startBtn.disabled = false;
        }
    });

    stopBtn.addEventListener('click', async () => {
        const originalText = stopBtn.innerHTML;
        stopBtn.disabled = true;
        stopBtn.textContent = "Shutting down...";
        
        try {
            await fetch('/api/stop', { method: 'POST' });
            addLog("Engine shutdown sequence initiated.", "system");
            setTimeout(updateStatus, 1000);
        } catch (e) {
            addLog("Termination failed.", "error");
            stopBtn.disabled = false;
            stopBtn.innerHTML = originalText;
        }
    });

    // Initial Poll
    updateStatus();
    pollInterval = setInterval(updateStatus, 2000);
});
