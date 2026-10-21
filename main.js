document.addEventListener("DOMContentLoaded", () => {
    const loginModal = document.getElementById("authModal");
    const registerModal = document.getElementById("registerModal");
    const passwordRegistroModal = document.getElementById("passwordRegistroModal");
    const openBtn = document.getElementById("openModalBtn");
    const closeBtn = document.getElementById("closeModal");
    const closeRegisterBtn = document.getElementById("closeRegisterModal");
    const closePasswordRegistroModalBtn = document.getElementById("closePasswordRegistroModal");
    const showRegisterModalBtn = document.getElementById("showRegisterModal");
    const showLoginModalBtn = document.getElementById("showLoginModal");
    const rolRegistroEspecialInput = document.getElementById("rolRegistroEspecial");
    const roleSelectorRegistro = document.getElementById("roleSelectorRegistro");
    
    // MODAL PRIVACIDAD
    const privacyModal = document.getElementById("privacyModal");
    const openPrivacyBtn = document.getElementById("openPrivacyModal");
    const closePrivacyBtn = document.getElementById("closePrivacyModal");
    const acceptPrivacyBtn = document.getElementById("acceptPrivacyModal");

    if (openPrivacyBtn && privacyModal) {
        openPrivacyBtn.onclick = (e) => {
            e.preventDefault();
            privacyModal.classList.add("open");
            document.body.style.overflow = 'hidden'; // Evitar scroll al abrir modal
        }
    }

    if (closePrivacyBtn && privacyModal) {
        closePrivacyBtn.onclick = () => {
            privacyModal.classList.remove("open");
            document.body.style.overflow = '';
        }
    }

    if (acceptPrivacyBtn && privacyModal) {
        acceptPrivacyBtn.onclick = () => {
            privacyModal.classList.remove("open");
            document.body.style.overflow = '';
        }
    }

    // Cerrar modal al hacer click fuera del contenido
    window.addEventListener('click', (event) => {
        if (event.target == privacyModal) {
            privacyModal.classList.remove("open");
            document.body.style.overflow = '';
        }
        if (event.target == passwordRegistroModal) {
            passwordRegistroModal.classList.remove("open");
            document.body.style.overflow = '';
        }
    });

    // Botón para cerrar la modal de contraseña
    if (closePasswordRegistroModalBtn && passwordRegistroModal) {
        closePasswordRegistroModalBtn.onclick = () => {
            passwordRegistroModal.classList.remove("open");
            document.body.style.overflow = '';
        }
    }

    // Manejar cambio de rol en el selector del modal de registro
    if (roleSelectorRegistro) {
        const roleRadios = roleSelectorRegistro.querySelectorAll('input[name="role"]');
        roleRadios.forEach(radio => {
            radio.addEventListener('change', (e) => {
                const selectedRole = e.target.value;
                const rolesEspeciales = ['docente', 'coordinador_ori', 'coordinador_area'];
                
                if (rolesEspeciales.includes(selectedRole)) {
                    // Desseleccionar el radio por ahora
                    e.target.checked = false;
                    // Seleccionar estudiante por defecto
                    const estudianteRadio = roleSelectorRegistro.querySelector('input[value="estudiante"]');
                    if (estudianteRadio) estudianteRadio.checked = true;
                    
                    // Mostrar modal de contraseña
                    if (rolRegistroEspecialInput) {
                        rolRegistroEspecialInput.value = selectedRole;
                    }
                    if (registerModal) registerModal.classList.remove("open");
                    if (passwordRegistroModal) {
                        passwordRegistroModal.classList.add("open");
                        document.body.style.overflow = 'hidden';
                    }
                }
            });
        });
    }

    // Manejar enlaces de registro especial
    document.querySelectorAll('a[href*="registro-docente"], a[href*="registro-ori"], a[href*="registro-coordinador"]').forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            let rol = '';
            if (link.getAttribute('href').includes('registro-docente')) {
                rol = 'docente';
            } else if (link.getAttribute('href').includes('registro-ori')) {
                rol = 'coordinador_ori';
            } else if (link.getAttribute('href').includes('registro-coordinador')) {
                rol = 'coordinador_area';
            }
            
            if (rolRegistroEspecialInput) {
                rolRegistroEspecialInput.value = rol;
            }
            
            if (passwordRegistroModal) {
                passwordRegistroModal.classList.add("open");
                document.body.style.overflow = 'hidden';
            }
        });
    });

    // MENÚ MÓVIL
    const mobileMenuBtn = document.getElementById('mobile-menu');
    const navLinksContainer = document.querySelector('.nav-links');

    if (mobileMenuBtn) {
        mobileMenuBtn.onclick = () => {
            navLinksContainer.classList.toggle('active'); 
            mobileMenuBtn.classList.toggle('is-active');  
        };
    }

    // Cerrar menú al hacer click en enlaces (excepto el dropdown en móvil)
    document.querySelectorAll('.nav-links a').forEach(link => {
        link.addEventListener('click', (e) => {
            // No cerrar si es el toggle del dropdown en móvil
            if (link.getAttribute('href') === '#') {
                if (window.innerWidth <= 768) {
                    return; // Permitir que el dropdown se maneje por CSS o clicks específicos
                }
            }
            navLinksContainer.classList.remove('active');
            mobileMenuBtn.classList.remove('is-active');
        });
    });

    // Abrir Modal de Login
    if(openBtn) {
        openBtn.onclick = () => {
            if(registerModal) registerModal.classList.remove("open");
            if(loginModal) loginModal.classList.add("open");
        }
    }

    // Cerrar Modales
    if(closeBtn) {
        closeBtn.onclick = () => loginModal.classList.remove("open");
    }
    
    if (closeRegisterBtn) {
        closeRegisterBtn.onclick = () => registerModal.classList.remove("open");
    }

    // Toggle Formularios (Abrir uno y cerrar otro)
    if(showRegisterModalBtn) {
        showRegisterModalBtn.onclick = (e) => {
            e.preventDefault();
            if(loginModal) loginModal.classList.remove("open");
            if(registerModal) registerModal.classList.add("open");
        }
    }

    if(showLoginModalBtn) {
        showLoginModalBtn.onclick = (e) => {
            e.preventDefault();
            if(registerModal) registerModal.classList.remove("open");
            if(loginModal) loginModal.classList.add("open");
        }
    }

    // 2. Lógica Botón Volver Arriba
    const backToTop = document.getElementById('backToTop');
    window.addEventListener('scroll', () => {
        if (window.pageYOffset > 300) {
            backToTop.classList.add('show');
        } else {
            backToTop.classList.remove('show');
        }
    });

    if (backToTop) {
        backToTop.onclick = () => {
            window.scrollTo({ top: 0, behavior: 'smooth' });
        };
    }

    // 3. Lógica Reveal on Scroll
    const reveal = () => {
        const reveals = document.querySelectorAll('.reveal');
        reveals.forEach(el => {
            const windowHeight = window.innerHeight;
            const elementTop = el.getBoundingClientRect().top;
            const elementVisible = 150;
            if (elementTop < windowHeight - elementVisible) {
                el.classList.add('active');
            }
        });
    }
    window.addEventListener('scroll', reveal);
    reveal(); // Ejecutar al cargar

    // 6. Confirmación Cierre de Sesión
    const logoutBtn = document.querySelector('a[href*="logout"]');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', (e) => {
            e.preventDefault();
            const logoutUrl = logoutBtn.getAttribute('href');
            Swal.fire({
                title: '¿Cerrar sesión?',
                text: "Tendrás que ingresar tus datos de nuevo para acceder.",
                icon: 'question',
                showCancelButton: true,
                confirmButtonColor: '#850000',
                cancelButtonColor: '#666',
                confirmButtonText: 'Sí, salir',
                cancelButtonText: 'Cancelar'
            }).then((result) => {
                if (result.isConfirmed) {
                    window.location.href = logoutUrl;
                }
            });
        });
    }

    // Ocultar/Mostrar campos de universidad y carrera según el rol
    const roleRadios = document.querySelectorAll('input[name="role"]');
    const uniGroup = document.getElementById('reg-universidad-group');
    const carreraGroup = document.getElementById('reg-carrera-group');
    const carreraSelect = document.getElementById('carrera-select');

    const listEstudianteCoord = [
        "Tecnologia Mtto Electrico y Tecnologia Mtto Mecanico",
        "BIOLOGIA MARINA",
        "CONTADURIA PUBLICA",
        "DERECHO",
        "ADMÓN NEGOCIOS INTERNACIONALES",
        "GASTRONOMIA",
        "INGENIERIA AGROINDUSTRIAL",
        "INGENIERIA CIVIL",
        "INGENIERIA DE SISTEMAS",
        "INGENIERIA INDUSTRIAL",
        "ENFERMERIA",
        "MEDICINA",
        "NUTRICION",
        "ODONTOLOGIA",
        "OPTOMETRIA",
        "FISIOTERAPIA",
        "PSICOLOGIA",
        "ADMON EMPRESAS TURISTICAS Y HOTELERAS",
        "Diseño industrial"
    ];

    const listDocentes = [
        "BASICAS EXACTAS",
        "Tecnologia Mtto Electrico y Tecnologia Mtto Mecanico",
        "BASICAS SALUD",
        "BIOLOGIA MARINA",
        "CONTADURIA PUBLICA",
        "DERECHO",
        "ADMÓN NEGOCIOS INTERNACIONALES",
        "GASTRONOMIA",
        "HUMANIDADES",
        "INGENIERIA AGROINDUSTRIAL",
        "INGENIERIA CIVIL",
        "INGENIERIA DE SISTEMAS",
        "INGENIERIA INDUSTRIAL",
        "POSGRADOS",
        "ENFERMERIA",
        "MEDICINA",
        "NUTRICION",
        "ODONTOLOGIA",
        "OPTOMETRIA",
        "FISIOTERAPIA",
        "PREVENTIVA",
        "PSICOLOGIA",
        "INVESTIGACIÓN FORMATIVA",
        "ADMON EMPRESAS TURISTICAS Y HOTELERAS",
        "ADMINISTRATIVO"
    ];

    function toTitleCase(str) {
        if (str === "ADMÓN NEGOCIOS INTERNACIONALES") return "Admón Negocios Internacionales";
        if (str === "ADMON EMPRESAS TURISTICAS Y HOTELERAS") return "Admón Empresas Turísticas y Hoteleras";
        if (str === "Tecnologia Mtto Electrico y Tecnologia Mtto Mecanico") return "Tecnología Mtto Eléctrico y Mecánico";
        if (str === "INVESTIGACIÓN FORMATIVA") return "Investigación Formativa";
        if (str === "BASICAS EXACTAS") return "Básicas Exactas";
        if (str === "BASICAS SALUD") return "Básicas Salud";
        return str.toLowerCase().replace(/(?:^|\s)\w/g, function(match) {
            return match.toUpperCase();
        });
    }

    function updateCarreraSelect(role) {
        if (!carreraSelect) return;
        
        carreraSelect.innerHTML = '';
        
        const defaultOption = document.createElement('option');
        defaultOption.value = '';
        defaultOption.disabled = true;
        defaultOption.selected = true;
        defaultOption.id = 'carrera-placeholder';
        
        if (role === 'estudiante') {
            defaultOption.textContent = 'Seleccione su Carrera';
            defaultOption.setAttribute('data-i18n-placeholder', 'reg-placeholder-career');
        } else {
            defaultOption.textContent = 'Seleccione su Programa';
        }
        
        carreraSelect.appendChild(defaultOption);

        let activeList = [];
        if (role === 'estudiante') {
            activeList = listEstudianteCoord;
        } else if (role === 'docente' || role === 'coordinador_area') {
            activeList = listDocentes;
        }

        activeList.forEach(item => {
            const option = document.createElement('option');
            option.value = item;
            option.textContent = toTitleCase(item);
            carreraSelect.appendChild(option);
        });
    }

    if (roleRadios.length > 0 && uniGroup && carreraGroup) {
        function handleRoleSelection(roleValue) {
            if (roleValue === 'coordinador_ori') {
                uniGroup.style.display = 'none';
                carreraGroup.style.display = 'none';
                if (carreraSelect) carreraSelect.required = false;
            } else {
                uniGroup.style.display = 'flex'; // input-group usa flex
                carreraGroup.style.display = 'flex';
                if (carreraSelect) carreraSelect.required = true;
                updateCarreraSelect(roleValue);
            }
        }

        // Inicializar la lista al cargar la página (basado en el rol seleccionado por defecto)
        const checkedRadio = document.querySelector('input[name="role"]:checked');
        if (checkedRadio) handleRoleSelection(checkedRadio.value);

        roleRadios.forEach(radio => {
            radio.addEventListener('change', (e) => {
                handleRoleSelection(e.target.value);
            });
        });
    }

    // Scroll Reveal
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) entry.target.classList.add("active");
        });
    }, { threshold: 0.1 });

    document.querySelectorAll(".reveal").forEach(el => observer.observe(el));

    // Contador Animado para Estadísticas
    const stats = document.querySelectorAll('.stat-number');
    const statsObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const target = parseInt(entry.target.getAttribute('data-target'));
                const prefix = entry.target.getAttribute('data-prefix') || '';
                
                const count = () => {
                    const current = parseInt(entry.target.innerText.replace(/[^0-9]/g, '')) || 0;
                    const increment = target / 50;
                    if (current < target) {
                        entry.target.innerText = prefix + Math.ceil(current + increment);
                        setTimeout(count, 30);
                    } else {
                        // Add commas for thousands
                        const formattedTarget = target.toLocaleString('es-CO');
                        entry.target.innerText = prefix + formattedTarget;
                    }
                };
                count();
                statsObserver.unobserve(entry.target);
            }
        });
    }, { threshold: 0.5 });

    stats.forEach(s => statsObserver.observe(s));
});
