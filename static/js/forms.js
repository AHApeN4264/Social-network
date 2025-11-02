document.addEventListener('DOMContentLoaded', () => {
    // Format card number with spaces
    const cardInput = document.getElementById('card-number');
    if (cardInput) {
        cardInput.addEventListener('input', (e) => {
            let value = e.target.value.replace(/\D/g, '');
            if (value.length > 16) value = value.slice(0, 16);
            e.target.value = value.replace(/(.{4})/g, '$1 ').trim();
        });
    }

    // Close button handling using CSS-first approach
    document.addEventListener('click', (e) => {
        if (e.target.matches('.close-button, .overlay')) {
            const checkboxes = document.querySelectorAll('input[type="checkbox"]');
            checkboxes.forEach(cb => cb.checked = false);
        }
    });

    // Simple form submissions
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', (e) => {
            if (!form.method || form.method.toLowerCase() !== 'post') return;
            
            e.preventDefault();
            const formData = new FormData(form);
            
            fetch(form.action, {
                method: 'POST',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': formData.get('csrfmiddlewaretoken'),
                },
                body: formData,
            })
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    alert(data.error);
                    return;
                }
                // Handle success - refresh page or update UI
                if (data.reload) {
                    window.location.reload();
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('An error occurred');
            });
        });
    });
});