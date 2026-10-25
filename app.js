document.addEventListener('DOMContentLoaded', () => {
  const viewAuth = document.getElementById('view-auth');
  const viewMain = document.getElementById('view-main');
  const authForm = document.getElementById('auth-form');
  const authHeading = document.getElementById('auth-heading');
  const authSubheading = document.getElementById('auth-subheading');
  const authSubmitBtn = document.getElementById('auth-submit-btn');
  const authTogglePrompt = document.getElementById('auth-toggle-prompt');
  const authToggleModeBtn = document.getElementById('auth-toggle-mode-btn');
  const navLoginBtn = document.getElementById('nav-login-btn');
  const navSignupBtn = document.getElementById('nav-signup-btn');
  const groupFullname = document.getElementById('group-fullname');
  const groupRepeatPassword = document.getElementById('group-repeat-password');
  const forgotPasswordLink = document.getElementById('forgot-password-link');
  const btnGoogleAuth = document.getElementById('btn-google-auth');
  const btnAppleAuth = document.getElementById('btn-apple-auth');
  const btnSignOut = document.getElementById('btn-sign-out');
  const togglePassBtn = document.getElementById('toggle-password-btn');
  const inputPassword = document.getElementById('input-password');
  const toggleRepeatPassBtn = document.getElementById('toggle-repeat-password-btn');
  const inputRepeatPassword = document.getElementById('input-repeat-password');
  const heroDynamicGreeting = document.getElementById('hero-dynamic-greeting');
  const filesListContainer = document.getElementById('files-list-container');
  const fileUploadInput = document.getElementById('file-upload-input');
  const btnTriggerUpload = document.getElementById('btn-trigger-upload');
  const chatMessagesThread = document.getElementById('chat-messages-thread');
  const chatForm = document.getElementById('chat-form');
  const chatUserInput = document.getElementById('chat-user-input');
  const chatActiveDocsCount = document.getElementById('chat-active-docs-count');
  const promptSuggestions = document.getElementById('prompt-suggestions');
  let isLoginMode = false;
  let uploadedFiles = [
    { name: 'Q4_Financial_Report.pdf', type: 'pdf', size: '2.4 MB' },
    { name: 'Security_Audit_2025.doc', type: 'doc', size: '840 KB' },
    { name: 'Growth_Metrics_Analysis.csv', type: 'csv', size: '1.1 MB' }
  ];
  function updateTimeGreeting() {
    const currentHour = new Date().getHours();
    let greetingTerm = 'night owl';
    let fullGreeting = '';
    if (currentHour >= 5 && currentHour < 12) {
      greetingTerm = 'early bird';
      fullGreeting = `Hey ${greetingTerm}, what are we exploring today?`;
    } else if (currentHour >= 12 && currentHour < 17) {
      greetingTerm = 'good afternoon';
      fullGreeting = `Good afternoon, what are we exploring today?`;
    } else if (currentHour >= 17 && currentHour < 22) {
      greetingTerm = 'good evening';
      fullGreeting = `Good evening, what are we exploring today?`;
    } else {
      greetingTerm = 'night owl';
      fullGreeting = `Hey ${greetingTerm}, what are we exploring today?`;
    }
    if (heroDynamicGreeting) {
      heroDynamicGreeting.textContent = fullGreeting;
    }
  }
  function showView(viewId) {
    if (viewId === 'main') {
      viewAuth.classList.remove('active');
      setTimeout(() => {
        viewMain.classList.add('active');
        updateTimeGreeting();
        renderFilesList();
        window.scrollTo({ top: 0, behavior: 'smooth' });
      }, 50);
    } else {
      viewMain.classList.remove('active');
      setTimeout(() => {
        viewAuth.classList.add('active');
        window.scrollTo({ top: 0, behavior: 'smooth' });
      }, 50);
    }
  }
  function setAuthMode(toLogin) {
    isLoginMode = toLogin;
    if (isLoginMode) {
      authHeading.textContent = 'Welcome back';
      authSubheading.textContent = 'Log in to your account';
      groupFullname.style.display = 'none';
      groupRepeatPassword.style.display = 'none';
      forgotPasswordLink.style.display = 'block';
      authSubmitBtn.textContent = 'Log in';
      authTogglePrompt.textContent = "Don't have an account?";
      authToggleModeBtn.textContent = 'Sign up';
      navLoginBtn.classList.remove('btn-ghost');
      navLoginBtn.classList.add('btn-primary');
      navSignupBtn.classList.remove('btn-primary');
      navSignupBtn.classList.add('btn-ghost');
    } else {
      authHeading.textContent = 'Create an account';
      authSubheading.textContent = 'Sign up and get started';
      groupFullname.style.display = 'flex';
      groupRepeatPassword.style.display = 'flex';
      forgotPasswordLink.style.display = 'none';
      authSubmitBtn.textContent = 'Complete & Sign up';
      authTogglePrompt.textContent = 'Already have an account?';
      authToggleModeBtn.textContent = 'Log in';
      navSignupBtn.classList.remove('btn-ghost');
      navSignupBtn.classList.add('btn-primary');
      navLoginBtn.classList.remove('btn-primary');
      navLoginBtn.classList.add('btn-ghost');
    }
  }

  authToggleModeBtn.addEventListener('click', () => {
    setAuthMode(!isLoginMode);
  });

  navLoginBtn.addEventListener('click', () => {
    setAuthMode(true);
    document.getElementById('input-identifier').focus();
  });

  navSignupBtn.addEventListener('click', () => {
    setAuthMode(false);
    document.getElementById('input-fullname').focus();
  });
  function setupPasswordToggle(button, input, iconId) {
    if (!button || !input) return;
    button.addEventListener('click', () => {
      const isPassword = input.type === 'password';
      input.type = isPassword ? 'text' : 'password';
      const icon = document.getElementById(iconId);
      if (icon) {
        icon.innerHTML = isPassword
          ? `<path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path><line x1="1" y1="1" x2="23" y2="23"></line>`
          : `<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path><circle cx="12" cy="12" r="3"></circle>`;
      }
    });
  }

  setupPasswordToggle(togglePassBtn, inputPassword, 'eye-icon-pass');
  setupPasswordToggle(toggleRepeatPassBtn, inputRepeatPassword, 'eye-icon-repeat');
  authForm.addEventListener('submit', (e) => {
    e.preventDefault();
    showView('main');
  });

  btnGoogleAuth.addEventListener('click', () => {
    showView('main');
  });

  btnAppleAuth.addEventListener('click', () => {
    showView('main');
  });

  btnSignOut.addEventListener('click', () => {
    showView('auth');
  });
  function getFileType(fileName) {
    const ext = fileName.split('.').pop().toLowerCase();
    if (ext === 'pdf') return 'pdf';
    if (ext === 'doc' || ext === 'docx') return 'doc';
    if (ext === 'csv') return 'csv';
    return 'txt';
  }

  function getFileIconSVG(type) {
    switch (type) {
      case 'pdf':
        return `<svg viewBox="0 0 24 24" fill="currentColor"><path d="M20 2H8c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm-8.5 7.5c0 .83-.67 1.5-1.5 1.5H9v2H7.5V7H10c.83 0 1.5.67 1.5 1.5v1zm5 2c0 .83-.67 1.5-1.5 1.5h-2.5V7H15c.83 0 1.5.67 1.5 1.5v3zm4-3H19v1h1.5V11H19v2h-1.5V7h3v1.5zM9 9.5h1v-1H9v1zm4.5 2h1v-3h-1v3zM4 6H2v14c0 1.1.9 2 2 2h14v-2H4V6z"/></svg>`;
      case 'doc':
        return `<svg viewBox="0 0 24 24" fill="currentColor"><path d="M14 2H6c-1.1 0-1.99.9-1.99 2L4 20c0 1.1.89 2 1.99 2H18c1.1 0 2-.9 2-2V8l-6-6zm2 16H8v-2h8v2zm0-4H8v-2h8v2zm-3-5V3.5L18.5 9H13z"/></svg>`;
      case 'csv':
        return `<svg viewBox="0 0 24 24" fill="currentColor"><path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zM9 17H7v-7h2v7zm4 0h-2V7h2v10zm4 0h-2v-4h2v4z"/></svg>`;
      default:
        return `<svg viewBox="0 0 24 24" fill="currentColor"><path d="M14 2H6c-1.1 0-2 .9-2 2v16c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V8l-6-6zM6 20V4h7v5h5v11H6z"/></svg>`;
    }
  }

  function renderFilesList() {
    filesListContainer.innerHTML = '';
    uploadedFiles.forEach((file, index) => {
      const chip = document.createElement('div');
      chip.className = 'file-chip';
      chip.innerHTML = `
        <div class="file-chip-left">
          <div class="file-chip-icon ${file.type}">
            ${getFileIconSVG(file.type)}
          </div>
          <span class="file-chip-name" title="${file.name}">${file.name}</span>
        </div>
        <button type="button" class="file-chip-remove" data-index="${index}" aria-label="Remove ${file.name}">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            <line x1="18" y1="6" x2="6" y2="18"></line>
            <line x1="6" y1="6" x2="18" y2="18"></line>
          </svg>
        </button>
      `;
      filesListContainer.appendChild(chip);
    });
    document.querySelectorAll('.file-chip-remove').forEach((btn) => {
      btn.addEventListener('click', (e) => {
        const idx = parseInt(e.currentTarget.getAttribute('data-index'), 10);
        uploadedFiles.splice(idx, 1);
        renderFilesList();
      });
    });
    if (chatActiveDocsCount) {
      chatActiveDocsCount.textContent = `${uploadedFiles.length} document${uploadedFiles.length === 1 ? '' : 's'} indexed`;
    }
  }

  btnTriggerUpload.addEventListener('click', () => {
    fileUploadInput.click();
  });

  fileUploadInput.addEventListener('change', (e) => {
    const files = Array.from(e.target.files);
    if (files.length > 0) {
      files.forEach((file) => {
        const type = getFileType(file.name);
        uploadedFiles.push({
          name: file.name,
          type: type,
          size: (file.size / 1024 / 1024).toFixed(1) + ' MB'
        });
      });
      renderFilesList();
      fileUploadInput.value = '';
      addBotMessage(`Successfully indexed **${files.length} new document${files.length === 1 ? '' : 's'}**. Vector embeddings and context compression completed. You can query them now!`);
    }
  });
  function addUserMessage(text) {
    const msgDiv = document.createElement('div');
    msgDiv.className = 'chat-message user';
    msgDiv.innerHTML = `
      <div class="message-bubble">${escapeHTML(text)}</div>
      <div class="message-meta">You · Just now</div>
    `;
    chatMessagesThread.appendChild(msgDiv);
    chatMessagesThread.scrollTop = chatMessagesThread.scrollHeight;
  }

  function addBotMessage(htmlContent) {
    const msgDiv = document.createElement('div');
    msgDiv.className = 'chat-message bot';
    msgDiv.innerHTML = `
      <div class="message-bubble">${htmlContent}</div>
      <div class="message-meta">DocuMind AI · Just now</div>
    `;
    chatMessagesThread.appendChild(msgDiv);
    chatMessagesThread.scrollTop = chatMessagesThread.scrollHeight;
  }

  function escapeHTML(str) {
    return str.replace(/[&<>'"]/g,
      tag => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[tag] || tag)
    );
  }

  function generateAIResponse(query) {
    const qLower = query.toLowerCase();
    setTimeout(() => {
      if (qLower.includes('financial') || qLower.includes('q4') || qLower.includes('highlight') || qLower.includes('revenue')) {
        addBotMessage(`
          <p><span class="citation-tag">Q4_Financial_Report.pdf · p. 4</span> <strong>Key Highlights:</strong></p>
          <ul style="margin: 8px 0 0 18px; line-height: 1.6;">
            <li><strong>Total Net Revenue:</strong> $18.4M, representing a <strong>+24.6% YoY growth</strong>.</li>
            <li><strong>Gross Margins:</strong> Expanded by 320 bps to <strong>78.4%</strong> due to cloud infrastructure optimizations.</li>
            <li><strong>Customer Retention:</strong> Net Dollar Retention (NDR) sustained at <strong>118%</strong> across enterprise cohorts.</li>
          </ul>
        `);
      } else if (qLower.includes('kpi') || qLower.includes('metric') || qLower.includes('csv')) {
        addBotMessage(`
          <p><span class="citation-tag">Growth_Metrics_Analysis.csv · Rows 12-48</span> <strong>Extracted Metrics:</strong></p>
          <ul style="margin: 8px 0 0 18px; line-height: 1.6;">
            <li><strong>Monthly Active Workspaces (MAW):</strong> 42,910 (+18.2% MoM)</li>
            <li><strong>Query Latency P99:</strong> 184ms via Gemini 2.0 Flash embeddings</li>
            <li><strong>Compression Ratio:</strong> 4.2x context reduction with zero semantic loss</li>
          </ul>
        `);
      } else if (qLower.includes('security') || qLower.includes('audit') || qLower.includes('compliance')) {
        addBotMessage(`
          <p><span class="citation-tag">Security_Audit_2025.doc · Sec. 3.2</span> <strong>Compliance & Security Status:</strong></p>
          <p style="margin-top: 6px;">The report confirms SOC2 Type II compliance with zero critical vulnerabilities. All document chunks in local Chroma DB are encrypted at rest with AES-256 and transit-protected with TLS 1.3.</p>
        `);
      } else {
        addBotMessage(`
          <p>I examined your ${uploadedFiles.length} active documents regarding <em>"${escapeHTML(query)}"</em>.</p>
          <p style="margin-top: 6px;">Cross-document synthesis reveals strong correlation between operational benchmarks and security measures outlined in your repository. Let me know if you would like me to draft an executive briefing or extract specific data tables!</p>
        `);
      }
    }, 600);
  }
  chatForm.addEventListener('submit', (e) => {
    e.preventDefault();
    const query = chatUserInput.value.trim();
    if (!query) return;

    addUserMessage(query);
    chatUserInput.value = '';
    generateAIResponse(query);
  });
  if (promptSuggestions) {
    promptSuggestions.addEventListener('click', (e) => {
      const chip = e.target.closest('.prompt-chip');
      if (chip) {
        const prompt = chip.getAttribute('data-prompt');
        if (prompt) {
          addUserMessage(prompt);
          generateAIResponse(prompt);
        }
      }
    });
  }
  function cleanSplineWatermarks() {
    const viewers = document.querySelectorAll('spline-viewer');
    viewers.forEach((viewer) => {
      const purge = () => {
        if (viewer.shadowRoot) {
          const logo = viewer.shadowRoot.querySelector('#logo') ||
            viewer.shadowRoot.querySelector('a[href*="spline.design"]') ||
            viewer.shadowRoot.querySelector('.spline-watermark');
          if (logo) {
            logo.remove();
          }
          if (!viewer.shadowRoot.querySelector('style[data-custom="clean-spline"]')) {
            const style = document.createElement('style');
            style.setAttribute('data-custom', 'clean-spline');
            style.textContent = `
              #logo, 
              a[href*="spline.design"],
              .spline-watermark,
              [id*="logo"],
              a {
                display: none !important;
                opacity: 0 !important;
                visibility: hidden !important;
                pointer-events: none !important;
                position: absolute !important;
                bottom: -9999px !important;
                right: -9999px !important;
                width: 0 !important;
                height: 0 !important;
                overflow: hidden !important;
              }
            `;
            viewer.shadowRoot.appendChild(style);
          }
        }
      };

      purge();

      const hide3DObject = () => {
        purge();
        try {
          if (typeof viewer.findObjectByName === 'function') {
            const rect = viewer.findObjectByName('Rectangle');
            if (rect) rect.visible = false;
          }
          if (typeof viewer.findObjectById === 'function') {
            const rectId = viewer.findObjectById('f8572186-b48b-494b-9721-a5dc70f8ee96');
            if (rectId) rectId.visible = false;
          }
        } catch (err) { }
      };

      viewer.addEventListener('load-complete', hide3DObject);
      viewer.addEventListener('load', hide3DObject);
      const timer = setInterval(hide3DObject, 80);
      setTimeout(() => clearInterval(timer), 7000);
    });
  }
  updateTimeGreeting();
  renderFilesList();
  cleanSplineWatermarks();
});
