# 🩺 Projeto de Realidade Virtual para Ensino em Pronto Socorro

**Disciplina:** PPGTI2003 - Interfaces de Visualização Avançada  
**Docente:** Prof. Rummenigge Rudson Dantas  
**Discente:** Joan de Azevedo Medeiros  

---

## 📌 Contexto
A professora **Katia**, do Departamento de Enfermagem da UFRN, necessita de uma aplicação de **Realidade Virtual (RV)** para apoiar o ensino de atendimento a pacientes em pronto socorro.  
O objetivo é criar uma solução de baixo custo, acessível e interativa, para ser utilizada em sala de aula e alcançar o maior número possível de alunos.  

O equipamento disponível é um **VR Box**, que utiliza um smartphone como tela e não possui rastreamento de mãos ou corpo.

---

## 🛑 Problema
- O **VR Box** não possui rastreamento de movimentos das mãos.  
- Não há controladores complexos disponíveis, apenas:
  - movimento da cabeça (gaze tracking básico);  
  - botão magnético ou controle Bluetooth simples.  
- Não há rastreamento de corpo inteiro.  

Isso limita a interação, tornando inviável a manipulação manual de objetos no ambiente virtual.

---

## 💡 Solução Proposta
A aplicação será baseada em **seleção por olhar (gaze-based selection)**.  
O usuário interage movendo a cabeça para apontar para opções na tela e confirmando ações ao manter o olhar fixo por alguns segundos.

### Características da solução
- **Interação simplificada:** seleção por olhar e, opcionalmente, botão magnético.  
- **Navegação controlada:** teletransporte por pontos pré-definidos no ambiente 3D.  
- **Feedback imediato:** reforço visual e sonoro a cada ação concluída.  
- **Foco educacional:** ênfase em **sequência de passos, tomada de decisão e reconhecimento de materiais**.

---

## 🧪 Procedimentos Simulados

### 1. Lavagem das mãos
- Molhar as mãos (olhar para a torneira).  
- Aplicar sabão (olhar para o dispenser).  
- Esfregar palmas, entre os dedos, pulsos e dorso das mãos (guiado por setas/indicações).  
- Enxaguar e secar (torneira + toalha/secador).  
- Feedback positivo ao concluir corretamente.

### 2. Preparação de medicamentos
- Selecionar o frasco/ampola.  
- Escolher a seringa correta.  
- Adicionar o medicamento.  
- Remover bolhas de ar.  
- Selecionar algodão/gaze.  
- Validação da sequência correta antes de avançar.  

### 3. Verificação de sinais vitais
- Posicionar o esfigmomanômetro no braço do paciente.  
- Inflar o manguito.  
- Observar leitura do medidor.  
- Utilizar o estetoscópio.  
- Responder perguntas interativas sobre os valores medidos.  
- Feedback em tempo real para reforço do aprendizado.

---

## ⚙️ Tecnologias e Ferramentas
- **Three.js / A-Frame** → para desenvolvimento do ambiente 3D em navegador.  
- **Smartphone + VR Box** → execução imersiva.  
- **HTML + JavaScript** → prototipagem simples e multiplataforma.  

---
