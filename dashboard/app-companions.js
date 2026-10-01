/**
 * app-companions.js — Frontend controller for Jared Rhodes' Companion Applications
 * (AI Visualizer & Barehands 3D Stage) inside the Hermes Brain Command Deck.
 */

(function () {
  const STATE = {
    visualizer: { online: false, state: 'idle', face: 'board' },
    barehands: { online: false, items_count: 0 },
    exploded: false,
    pipOpen: false,
  };

  async function fetchStatus() {
    try {
      const res = await fetch('/api/companions/status');
      if (!res.ok) return;
      const data = await res.json();

      STATE.visualizer = data.visualizer || STATE.visualizer;
      STATE.barehands = data.barehands || STATE.barehands;

      updateUI();
    } catch (e) {
      // Server down or network error
    }
  }

  function updateUI() {
    // 1. Header indicators
    const visDot = document.getElementById('header-vis-dot');
    if (visDot) {
      visDot.className = `hud-status-dot vis-dot ${STATE.visualizer.online ? 'online' : 'offline'}`;
      visDot.title = `AI Visualizer (Port 8790): ${STATE.visualizer.online ? 'Online (' + STATE.visualizer.state + ')' : 'Offline'}`;
    }

    const bhDot = document.getElementById('header-bh-dot');
    if (bhDot) {
      bhDot.className = `hud-status-dot bh-dot ${STATE.barehands.online ? 'online' : 'offline'}`;
      bhDot.title = `Barehands 3D Stage (Port 8794): ${STATE.barehands.online ? 'Online (' + STATE.barehands.items_count + ' items)' : 'Offline'}`;
    }

    // 2. View section indicators
    const visViewDot = document.getElementById('vis-pulse-dot');
    const visViewText = document.getElementById('vis-status-text');
    if (visViewDot) {
      visViewDot.className = `status-pulse-dot ${STATE.visualizer.online ? 'online' : 'offline'}`;
    }
    if (visViewText) {
      visViewText.textContent = `Visualizer • ${STATE.visualizer.online ? STATE.visualizer.state.toUpperCase() : 'OFFLINE'}`;
    }

    const bhViewDot = document.getElementById('bh-pulse-dot');
    const bhViewText = document.getElementById('bh-status-text');
    if (bhViewDot) {
      bhViewDot.className = `status-pulse-dot ${STATE.barehands.online ? 'online' : 'offline'}`;
    }
    if (bhViewText) {
      bhViewText.textContent = `Bare Hands 3D • ${STATE.barehands.online ? STATE.barehands.items_count + ' ITEM(S)' : 'OFFLINE'}`;
    }

    // 3. Sync face selector if not focused
    const faceSelect = document.getElementById('vis-face-select');
    if (faceSelect && document.activeElement !== faceSelect && STATE.visualizer.face) {
      faceSelect.value = STATE.visualizer.face;
    }
  }

  // Public Controller API
  window.HermesCompanions = {
    async setVisualizerState(state) {
      try {
        await fetch('/api/companions/visualizer/state', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ state }),
        });
        fetchStatus();
      } catch (e) {
        console.error('Failed to set visualizer state:', e);
      }
    },

    async setVisualizerFace(face) {
      try {
        await fetch('/api/companions/visualizer/face', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ face }),
        });
        // Reload iframes
        this.reloadVisualizer();
        fetchStatus();
      } catch (e) {
        console.error('Failed to set visualizer face:', e);
      }
    },

    reloadVisualizer() {
      const iframe = document.getElementById('iframe-visualizer');
      if (iframe) iframe.src = iframe.src;
      const pipIframe = document.getElementById('pip-iframe');
      if (pipIframe) pipIframe.src = pipIframe.src;
    },

    reloadBarehands() {
      const iframe = document.getElementById('iframe-barehands');
      if (iframe) iframe.src = iframe.src;
    },

    async clearBoard() {
      try {
        await fetch('/api/companions/barehands/clear', { method: 'POST' });
        fetchStatus();
      } catch (e) {
        console.error('Failed to clear board:', e);
      }
    },

    async explodeModel() {
      STATE.exploded = !STATE.exploded;
      const action = STATE.exploded ? 'explode' : 'assemble';
      try {
        await fetch('/api/companions/barehands/cmd', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ a: action }),
        });
        fetchStatus();
      } catch (e) {
        console.error(`Failed to ${action} model:`, e);
      }
    },

    async resetBoard() {
      try {
        await fetch('/api/companions/barehands/cmd', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ a: 'reset' }),
        });
        fetchStatus();
      } catch (e) {
        console.error('Failed to reset board:', e);
      }
    },

    async presentCard(title, body) {
      try {
        const res = await fetch('/api/companions/barehands/present', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ title, body }),
        });
        if (res.ok) {
          // Trigger visual feedback notification
          if (window.CommandDeckInstance && typeof window.CommandDeckInstance.showToast === 'function') {
            window.CommandDeckInstance.showToast('Card presented on 3D Air-Board', 'success');
          }
        }
        fetchStatus();
      } catch (e) {
        console.error('Failed to present card:', e);
      }
    },

    togglePiP() {
      const drawer = document.getElementById('companion-pip-drawer');
      if (!drawer) return;
      STATE.pipOpen = !STATE.pipOpen;
      drawer.style.display = STATE.pipOpen ? 'flex' : 'none';
      if (STATE.pipOpen) {
        this.reloadVisualizer();
      }
    },

    expandPiPToView() {
      this.togglePiP();
      if (window.CommandDeckInstance && typeof window.CommandDeckInstance.switchView === 'function') {
        window.CommandDeckInstance.switchView('visualizer');
      }
    },

    async stageCurrentTasks() {
      if (!window.CommandDeckInstance || !window.CommandDeckInstance.state || !window.CommandDeckInstance.state.tasks) {
        return;
      }
      const tasks = window.CommandDeckInstance.state.tasks.filter(t => t.status !== 'completed').slice(0, 5);
      if (tasks.length === 0) {
        this.presentCard('Tasks Pipeline', 'All tasks are complete! Pipeline is clear.');
        return;
      }
      const body = tasks.map(t => `- [ ] **${t.title}**${t.priority === 'critical' ? ' 🔥' : ''}`).join('\n');
      await this.presentCard('Active Task Pipeline', body);
    },
  };

  // Wire event listeners once DOM is ready
  document.addEventListener('DOMContentLoaded', () => {
    // Face selector change listener
    const faceSelect = document.getElementById('vis-face-select');
    if (faceSelect) {
      faceSelect.addEventListener('change', (e) => {
        window.HermesCompanions.setVisualizerFace(e.target.value);
      });
    }

    // PiP toggle buttons
    const btnPiP = document.getElementById('btn-toggle-pip');
    if (btnPiP) {
      btnPiP.addEventListener('click', () => {
        window.HermesCompanions.togglePiP();
      });
    }

    const hudChip = document.getElementById('companion-hud-chip');
    if (hudChip) {
      hudChip.addEventListener('click', () => {
        window.HermesCompanions.togglePiP();
      });
    }

    // Initial status fetch and polling every 3 seconds
    fetchStatus();
    setInterval(fetchStatus, 3000);
  });
})();
