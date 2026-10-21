document.addEventListener("DOMContentLoaded", () => {
    console.log("unisinu_core.js cargado y ejecutándose");
    
    let unisinuClickCount = 0;
    let lastClickTime = 0;
    let unisinuAttempts = 3;
    let currentLangIndex = 0;
    let unisinuTimer = null;
    let unisinuTimeLeft = 10;

    const langOptions = [
        {
            name: "ruso",
            question: "Кто является командой разработчиков этого проекта?",
            fontFamily: "Arial, sans-serif",
            color: "#333"
        },
        {
            name: "alemán",
            question: "Wer ist das Entwicklerteam dieses Projekts?",
            fontFamily: "Arial, sans-serif",
            color: "#333"
        },
        {
            name: "árabe",
            question: "من هو فريق تطوير هذا المشروع؟",
            fontFamily: "Arial, sans-serif",
            color: "#333"
        },
        {
            name: "chino",
            question: "谁是这个项目的开发团队？",
            fontFamily: "Arial, sans-serif",
            color: "#333"
        }
    ];

    const alertStyles = [
        { fontFamily: "Impact, Haettenschweiler, sans-serif", color: "#ff0000" },
        { fontFamily: "Arial Black, Gadget, sans-serif", color: "#8b0000" },
        { fontFamily: "Comic Sans MS, cursive, sans-serif", color: "#ff4500" }
    ];

    const validKey = "-... .. -. .--- ..- / - . .- -- -.";

    const brandZone = document.getElementById('brandZone');
    const mainLogo = document.getElementById('mainLogo');
    const secretModal = document.getElementById('unisinuSecretModal');
    const closeSecretBtn = document.getElementById('closeUnisinuSecret');
    const secretQuestion = document.getElementById('unisinuSecretQuestion');
    const secretInput = document.getElementById('unisinuSecretInput');
    const secretSubmit = document.getElementById('unisinuSecretSubmit');
    const secretAttempts = document.getElementById('unisinuSecretAttempts');
    const secretContent = document.getElementById('unisinuSecretContent');
    const secretTitle = document.getElementById('unisinuSecretTitle');
    const secretBody = document.getElementById('unisinuSecretBody');
    const secretTimer = document.getElementById('unisinuSecretTimer');
    
    console.log("📋 Elementos encontrados:", {
        brandZone: !!brandZone,
        mainLogo: !!mainLogo,
        secretModal: !!secretModal
    });

    function stopUnisinuTimer() {
        if (unisinuTimer) {
            clearInterval(unisinuTimer);
            unisinuTimer = null;
        }
    }

    function startUnisinuTimer() {
        stopUnisinuTimer();
        unisinuTimeLeft = 10;
        updateTimerDisplay();
        
        unisinuTimer = setInterval(() => {
            unisinuTimeLeft--;
            updateTimerDisplay();
            
            if (unisinuTimeLeft <= 0) {
                stopUnisinuTimer();
                showFinalAlert();
            }
        }, 1000);
    }

    function updateTimerDisplay() {
        if (secretTimer) {
            secretTimer.textContent = `⏱️ Tiempo restante: ${unisinuTimeLeft}s`;
            if (unisinuTimeLeft <= 3) {
                secretTimer.style.color = "#ff0000";
                secretTimer.style.fontSize = "28px";
            } else {
                secretTimer.style.color = "#850000";
                secretTimer.style.fontSize = "24px";
            }
        }
    }

    function resetUnisinuSecret() {
        unisinuClickCount = 0;
        unisinuAttempts = 3;
        currentLangIndex = Math.floor(Math.random() * langOptions.length);
        stopUnisinuTimer();
    }

    function getCurrentLang() {
        return langOptions[currentLangIndex % langOptions.length];
    }

    function updateSecretUI() {
        const lang = getCurrentLang();
        const styleIdx = 3 - unisinuAttempts;
        
        let currentStyle;
        if (styleIdx > 0) {
            currentStyle = alertStyles[Math.min(styleIdx - 1, alertStyles.length - 1)];
        } else {
            currentStyle = lang;
        }

        secretQuestion.textContent = lang.question;
        secretQuestion.style.fontFamily = currentStyle.fontFamily;
        secretQuestion.style.color = currentStyle.color;
        secretQuestion.style.fontSize = styleIdx > 0 ? `${18 + styleIdx * 4}px` : "18px";
        secretQuestion.style.fontWeight = styleIdx > 0 ? "bold" : "normal";
        
        secretAttempts.textContent = `Intentos restantes: ${unisinuAttempts}`;
        
        secretInput.value = '';
        secretInput.placeholder = "Ingrese la respuesta...";
    }

    function openSecretModal() {
        currentLangIndex = Math.floor(Math.random() * langOptions.length);
        unisinuAttempts = 3;
        updateSecretUI();
        secretModal.classList.add('open');
        document.body.style.overflow = 'hidden';
        startUnisinuTimer();
    }

    function showFinalAlert() {
        secretBody.innerHTML = `
            <div style="text-align: center;">
                <h2 style="color: #ff0000; font-size: 32px; font-family: Impact, sans-serif;">⚠️ ACCESO RESTRINGIDO ⚠️</h2>
                <div style="margin: 30px 0;">
                    <img src="https://i.pinimg.com/736x/5c/58/e5/5c58e565679335e922512d1cf1717bc4.jpg" alt="Acceso Restringido" style="max-width: 100%; border-radius: 10px;">
                </div>
                <p style="color: #666; margin-top: 20px;">Cerrando sesión...</p>
            </div>
        `;
        
        setTimeout(() => {
            window.close();
        }, 3000);
    }

    function showWelcomeMessage() {
        secretBody.innerHTML = `
            <div style="text-align: left;">
                <h2 style="color: #28a745; font-size: 28px; text-align: center;">¡Felicidades!!!</h2>
                <div style="margin: 30px 0; padding: 0 10px;">
                    <p style="font-size: 16px; line-height: 1.8; margin-bottom: 20px;">
                        Descubriste este pequeño secreto, este mensaje es de parte de los desarrolladores de esta app Juanma y Francisco.
                    </p>
                    <p style="font-size: 16px; line-height: 1.8; margin-bottom: 20px;">
                        Queremos contarte nuestra experiencia desarrollando esta app, realmente este fue un proceso estresante y muy desorganizado, hicimos lo que pudimos en menos de 3 meses, hubieron tropiezos, retrasos y sobre todo bastantes pero bastantes horas sin dormir.
                    </p>
                    <p style="font-size: 16px; line-height: 1.8; margin-bottom: 20px;">
                        Principalmente queremos felicitarte por descubrir este pequeño mensaje, gracias por leerlo.
                    </p>
                    <p style="font-size: 16px; line-height: 1.8; margin-bottom: 30px; font-style: italic; color: #666;">
                        (Si eres el próximo practicante de relaciones internacionales, mucha suerte y recuerda que la paciencia será tu mayor virtud)
                    </p>
                    <p style="text-align: center; font-size: 14px; color: #666; border-top: 1px solid #eee; padding-top: 20px;">
                        Desarrollado con ❤️ por el Binju Team
                    </p>
                </div>
            </div>
        `;
    }

    function validateSecret() {
        stopUnisinuTimer();
        const answer = secretInput.value.trim().toLowerCase();
        
        if (answer === validKey) {
            showWelcomeMessage();
        } else {
            unisinuAttempts--;
            
            if (unisinuAttempts <= 0) {
                showFinalAlert();
            } else {
                currentLangIndex++;
                updateSecretUI();
                Swal.fire({
                    icon: 'error',
                    title: 'Respuesta inválida',
                    text: `Te quedan ${unisinuAttempts} intentos`,
                    confirmButtonColor: '#850000'
                }).then(() => {
                    startUnisinuTimer();
                });
            }
        }
    }

    if (brandZone || mainLogo) {
        const clickTarget = brandZone || mainLogo;
        console.log("Elemento de click encontrado, agregando listener:", clickTarget);
        
        clickTarget.addEventListener('click', (e) => {
            const now = Date.now();
            
            if (now - lastClickTime > 2000) {
                unisinuClickCount = 0;
            }
            
            unisinuClickCount++;
            lastClickTime = now;
            
            console.log("👆 Click registrado:", unisinuClickCount, "/10");
            
            if (unisinuClickCount >= 10) {
                e.preventDefault();
                unisinuClickCount = 0;
                console.log("🎉 10 clicks! Abriendo modal...");
                openSecretModal();
            } else if (unisinuClickCount >= 7) {
                mainLogo.style.transform = `scale(${1 + (unisinuClickCount - 7) * 0.1}) rotate(${(unisinuClickCount - 7) * 5}deg)`;
                setTimeout(() => {
                    mainLogo.style.transform = '';
                }, 200);
            } else if (unisinuClickCount === 1) {
                setTimeout(() => {
                    if (unisinuClickCount === 1) {
                        window.location.href = window.homeUrl || '/';
                    }
                }, 300);
            }
        });
    } else {
        console.error("❌ NO SE ENCONTRÓ NINGÚN ELEMENTO DE LOGO! brandZone:", brandZone, "mainLogo:", mainLogo);
    }

    if (closeSecretBtn && secretModal) {
        closeSecretBtn.onclick = () => {
            secretModal.classList.remove("open");
            document.body.style.overflow = '';
            resetUnisinuSecret();
        }
    }

    if (secretSubmit) {
        secretSubmit.onclick = validateSecret;
    }

    if (secretInput) {
        secretInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                validateSecret();
            }
        });
    }

    window.addEventListener('click', (event) => {
        if (event.target == secretModal) {
            secretModal.classList.remove("open");
            document.body.style.overflow = '';
            resetUnisinuSecret();
        }
    });
});
