// Sequência correta
const ordemCorreta = ["mascara", "luva", "estetoscopio"];
let escolha = [];

// Componente para seleção dos objetos
AFRAME.registerComponent("selecionavel", {
    schema: { id: { type: "string" } },
    init: function () {
        this.el.addEventListener("click", () => {
            escolha.push(this.data.id);
            if (escolha.length === ordemCorreta.length) {
                if (JSON.stringify(escolha) === JSON.stringify(ordemCorreta)) {
                    alert("✅ Sequência correta! Procedimento iniciado.");
                } else {
                    alert("❌ Ordem incorreta. Tente novamente.");
                }
                escolha = []; // reinicia
            }
        });
    },
});

// Componente para rotacionar objetos
AFRAME.registerComponent("rotacionavel", {
    init: function () {
        let el = this.el;
        let isDragging = false;
        let previousX, previousY;

        // Mouse
        el.sceneEl.addEventListener("mousedown", (e) => {
            isDragging = true;
            previousX = e.clientX;
            previousY = e.clientY;
        });
        el.sceneEl.addEventListener("mouseup", () => { isDragging = false; });
        el.sceneEl.addEventListener("mousemove", (e) => {
            if (!isDragging) return;
            let deltaX = e.clientX - previousX;
            let deltaY = e.clientY - previousY;

            let rotation = el.getAttribute("rotation");
            rotation.y += deltaX * 0.5;
            rotation.x -= deltaY * 0.5;

            el.setAttribute("rotation", rotation);
            previousX = e.clientX;
            previousY = e.clientY;
        });

        // Touch
        el.sceneEl.addEventListener("touchstart", (e) => {
            isDragging = true;
            previousX = e.touches[0].clientX;
            previousY = e.touches[0].clientY;
        });
        el.sceneEl.addEventListener("touchend", () => { isDragging = false; });
        el.sceneEl.addEventListener("touchmove", (e) => {
            if (!isDragging) return;
            let deltaX = e.touches[0].clientX - previousX;
            let deltaY = e.touches[0].clientY - previousY;

            let rotation = el.getAttribute("rotation");
            rotation.y += deltaX * 0.5;
            rotation.x -= deltaY * 0.5;

            el.setAttribute("rotation", rotation);
            previousX = e.touches[0].clientX;
            previousY = e.touches[0].clientY;
        });
    },
});
