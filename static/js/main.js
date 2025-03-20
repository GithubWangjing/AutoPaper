document.addEventListener('DOMContentLoaded', function() {
    const paperForm = document.getElementById('paperForm');
    const progressSection = document.getElementById('progressSection');
    const resultSection = document.getElementById('resultSection');
    const errorSection = document.getElementById('errorSection');
    const generateBtn = document.getElementById('generateBtn');
    const modelInputs = document.querySelectorAll('input[name="modelType"]');

    let progressInterval;
    let currentModel = 'openai';

    // Handle model selection
    modelInputs.forEach(input => {
        input.addEventListener('change', async function() {
            currentModel = this.value;
            try {
                const response = await fetch('/set-model', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ model_type: currentModel })
                });

                if (!response.ok) {
                    throw new Error('Failed to set model');
                }
            } catch (error) {
                document.getElementById('errorMessage').textContent = error.message;
                errorSection.classList.remove('d-none');
            }
        });
    });

    paperForm.addEventListener('submit', async function(e) {
        e.preventDefault();

        const topic = document.getElementById('topic').value;

        // Reset and show progress section
        progressSection.classList.remove('d-none');
        resultSection.classList.add('d-none');
        errorSection.classList.add('d-none');
        generateBtn.disabled = true;

        // Start progress polling
        startProgressPolling();

        try {
            const response = await fetch('/generate-paper', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ topic: topic })
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'Failed to generate paper');
            }

            // Stop progress polling
            clearInterval(progressInterval);

            // Display results - using innerHTML since we're receiving sanitized HTML
            document.getElementById('paperContent').innerHTML = data.paper;
            resultSection.classList.remove('d-none');
        } catch (error) {
            clearInterval(progressInterval);
            document.getElementById('errorMessage').textContent = error.message;
            errorSection.classList.remove('d-none');
        } finally {
            generateBtn.disabled = false;
        }
    });

    function startProgressPolling() {
        updateProgress();
        progressInterval = setInterval(updateProgress, 1000);
    }

    async function updateProgress() {
        try {
            const response = await fetch('/progress');
            const progress = await response.json();

            document.getElementById('researchProgress').style.width = `${progress.research}%`;
            document.getElementById('writingProgress').style.width = `${progress.writing}%`;
            document.getElementById('reviewProgress').style.width = `${progress.review}%`;
        } catch (error) {
            console.error('Error updating progress:', error);
        }
    }
});