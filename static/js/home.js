function checkCardsAndOpenDeposit() {
    const cardsList = document.getElementById('cards-list');
    const noCardsMessage = '{% if lang == "Українська" %}Карт не додано{% else %}No cards added{% endif %}';
    
    if (cardsList.textContent.includes(noCardsMessage)) {
        // No cards - redirect to add card form
        openAdd_card('add_card');
        document.getElementById('add-card-result').textContent = '{% if lang == "Українська" %}Спочатку додайте картку{% else %}Please add a card first{% endif %}';
    } else {
        // Has cards - open deposit form
        openSubscribe('deposit');
    }
}
function performDeposit() {
    const amount = document.getElementById('deposit-amount').value;
    const cardSelect = document.getElementById('deposit-card');
    
    if (!cardSelect || !cardSelect.value) {
        document.getElementById('deposit-result').textContent = '{% if lang == "Українська" %}Будь ласка, додайте картку{% else %}Please add a card first{% endif %}';
        return;
    }
    
    if (!amount || isNaN(amount) || amount <= 0) {
        document.getElementById('deposit-result').textContent = '{% if lang == "Українська" %}Будь ласка, введіть правильну суму{% else %}Please enter a valid amount{% endif %}';
        return;
    }
    fetch('/deposit-funds/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify({
            amount: amount,
            card_last4: cardSelect.value
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            document.getElementById('wallet-amount').textContent = `{% if lang == "Українська" %}Гаманець{% else %}Wallet{% endif %}: ${data.new_balance}`;
            document.getElementById('deposit-wallet').textContent = data.new_balance;
            document.getElementById('deposit-amount').value = '';
            document.getElementById('deposit-result').textContent = '{% if lang == "Українська" %}Успішно поповнено!{% else %}Successfully deposited!{% endif %}';
        } else {
            document.getElementById('deposit-result').textContent = data.error || '{% if lang == "Українська" %}Помилка при поповненні{% else %}Error depositing funds{% endif %}';
        }
    })
    .catch(error => {
        console.error('Error:', error);
        document.getElementById('deposit-result').textContent = '{% if lang == "Українська" %}Помилка при поповненні{% else %}Error depositing funds{% endif %}';
    });
}


document.addEventListener('DOMContentLoaded', () => {
    // localized card messages (from view)
    const cardMessages = {
        invalid_card_number: "{{ card_messages.invalid_card_number }}",
        card_added: "{{ card_messages.card_added }}",
        add_card_failed: "{{ card_messages.add_card_failed }}",
        cards_label: "{{ card_messages.cards_label }}",
        no_cards: "{{ card_messages.no_cards }}",
    };
    const tagElement = document.getElementById('user-tag');
    if (tagElement) {
        tagElement.addEventListener('click', () => {
            const text = tagElement.textContent;
            navigator.clipboard.writeText(text)
                .then(() => alert('Tag copied!'))
                .catch(err => console.error('Error copying tag:', err));
        });
    }

    // Close forms when clicking outside
    document.addEventListener('mousedown', (event) => {
        const forms = [
            { form: '.side-menu', toggle: '#menu-toggle' },
            { form: '.wallet-form', toggle: '#wallet-toggle' },
            { form: '.profile-form', toggle: '#profile-toggle' },
            { form: '.setting-form', toggle: '#setting-toggle' },
            { form: '.form1', toggle: '#form1-toggle' },
            { form: '.form2', toggle: '#form2-toggle' },
            { form: '.deposit-form', toggle: '#deposit-toggle' },
            { form: '.add_card-form', toggle: '#add_card-toggle' }
        ];

        forms.forEach(({form, toggle}) => {
            const formElement = document.querySelector(form);
            const toggleElement = document.querySelector(toggle);
            
            if (formElement && toggleElement && toggleElement.checked) {
                if (!formElement.contains(event.target) && !event.target.closest(form)) {
                    toggleElement.checked = false;
                }
            }
        });
    });

    const overlays = document.querySelectorAll('.overlay, .profile-overlay, .setting-overlay, .form1-overlay, .form2-overlay, .wallet-overlay, .subscribe-month-overlay, .subscribe-year-overlay, .deposit-overlay, .add_card-overlay');
    overlays.forEach(overlay => {
        overlay.addEventListener('click', () => {
            const checkboxes = document.querySelectorAll('#menu-toggle, #profile-toggle, #setting-toggle, #form1-toggle, #form2-toggle, #wallet-toggle, #subscribe-month-toggle, #subscribe-year-toggle, #deposit-toggle, #add_card-toggle');
            checkboxes.forEach(cb => {
                if(cb) cb.checked = false;
            });
        });
    });

    const depositInput = document.getElementById('deposit-amount');
    const depositResult = document.getElementById('deposit-result');
    const depositWalletSpan = document.getElementById('deposit-wallet');
    const currencySelect = document.querySelector('.wallet form select');

    function parseAmountAndCurrency(text) {
        if (!text) return { amount: 0, currency: ("{{ user.currency|default:'USD' }}") };
        const t = text.replace(/,/g, '').trim();
        const uah = t.indexOf('₴') !== -1 || /UAH/i.test(t);
        const usd = t.indexOf('$') !== -1 || /USD/i.test(t);
        const m = t.match(/([-+]?\d*\.?\d+)/);
        const amount = m ? Number(m[0]) : 0;
        const currency = uah ? 'UAH' : (usd ? 'USD' : ("{{ user.currency|default:'USD' }}"));
        return { amount, currency };
    }

    function formatCurrency(amount, currency) {
        if (amount === null || amount === undefined) return '';
        const a = Number(amount) || 0;
        if (currency === 'UAH') return a.toFixed(2) + ' ₴';
        return a.toFixed(2) + ' $';
    }

    function convertAmount(value, sourceCurrency, targetCurrency) {
        const v = Number(value) || 0;
        if (sourceCurrency === targetCurrency) return v;
        if (sourceCurrency === 'USD' && targetCurrency === 'UAH') return v * 42.1;
        if (sourceCurrency === 'UAH' && targetCurrency === 'USD') return v / 42.1;
        return v;
    }

    function updateDepositResult() {
        if (!depositInput || !depositResult || !depositWalletSpan) return;

        const walletRaw = depositWalletSpan.textContent || depositWalletSpan.innerText || '';
        const wallet = parseAmountAndCurrency(walletRaw);

        const depositVal = Number(depositInput.value) || 0;
        const depositCurrency = (currencySelect && currencySelect.value) ? currencySelect.value : ("{{ user.currency|default:'USD' }}");

    const depositConverted = convertAmount(depositVal, depositCurrency, wallet.currency);
    const total = (Number(wallet.amount) || 0) + depositConverted;

    const pageLang = "{{ user.language|default:'English' }}";
    const willBeText = pageLang === 'Українська' ? 'Буде' : 'Will be';
    depositResult.textContent = depositVal ? `${willBeText}: ${formatCurrency(total, wallet.currency)}` : '';
    }

    // Card number auto-format: add space every 4 digits and preserve caret
    function formatCardNumber(val) {
        // limit to 16 digits (typical card length). Format as '#### #### #### ####'
        const digits = val.replace(/\D/g, '').slice(0, 16);
        return digits.replace(/(.{4})/g, '$1 ').trim();
    }

    const cardNumberInput = document.getElementById('card-number');
    if (cardNumberInput) {
        // format on input and on paste
        cardNumberInput.addEventListener('input', (e) => {
            const el = e.target;
            const selectionStart = el.selectionStart || 0;
            // count digits before cursor
            const rawBefore = el.value.slice(0, selectionStart).replace(/\D/g, '');
            const formatted = formatCardNumber(el.value);
            el.value = formatted;
            // set caret after same number of digits
            let pos = 0;
            let digitsSeen = 0;
            while (digitsSeen < rawBefore.length && pos < el.value.length) {
                if (/\d/.test(el.value.charAt(pos))) digitsSeen++;
                pos++;
            }
            el.setSelectionRange(pos, pos);
        });
        cardNumberInput.addEventListener('paste', (e) => {
            e.preventDefault();
            const paste = (e.clipboardData || window.clipboardData).getData('text') || '';
            const digits = paste.replace(/\D/g, '').slice(0, 16);
            cardNumberInput.value = formatCardNumber(digits);
        });
    }

    if (depositInput) {
        depositInput.addEventListener('input', updateDepositResult);
    }
    if (currencySelect) {
        currencySelect.addEventListener('change', updateDepositResult);
    }

    window.performDeposit = function() {
        if (!depositInput || !depositWalletSpan) return;
        const v = Number(depositInput.value) || 0;
        if (v <= 0) {
            alert('Please enter an amount greater than 0');
            return;
        }

        const depositCurrency = (currencySelect && currencySelect.value) ? currencySelect.value : ("{{ user.currency|default:'USD' }}");

        const csrfInput = document.querySelector('input[name="csrfmiddlewaretoken"]');
        const csrf = csrfInput ? csrfInput.value : '';

        const formData = new FormData();
        formData.append('amount', v);
        formData.append('currency', depositCurrency);

        fetch('{% url "deposit-funds" %}', {
            method: 'POST',
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': csrf,
            },
            body: formData,
        })
        .then(resp => {
            if (!resp.ok) throw new Error('Network response was not ok');
            return resp.json();
        })
        .then(data => {
            if (data && data.price_converted) {
                depositWalletSpan.textContent = data.price_converted;
                const walletAmountEl = document.getElementById('wallet-amount');
                if (walletAmountEl) walletAmountEl.textContent = 'Wallet: ' + data.price_converted;
                const depositToggle = document.getElementById('deposit-toggle');
                const walletToggle = document.getElementById('wallet-toggle');
                if (depositToggle) depositToggle.checked = false;
                if (walletToggle) walletToggle.checked = true;
                depositInput.value = '';
                if (depositResult) depositResult.textContent = '';
            } else if (data && data.error) {
                alert('Deposit failed: ' + data.error);
            }
        })
        .catch(err => {
            console.error('Deposit failed:', err);
            alert('Deposit failed');
        });
    };

    window.openSubscribe = function(period) {
        const monthToggle = document.getElementById('subscribe-month-toggle');
        const yearToggle = document.getElementById('subscribe-year-toggle');

            if (period === 'month') {
                if (monthToggle) monthToggle.checked = true;
                if (yearToggle) yearToggle.checked = false;
                const depositToggle = document.getElementById('deposit-toggle');
                if (depositToggle) depositToggle.checked = false;
            } else if (period === 'year') {
                if (yearToggle) yearToggle.checked = true;
                if (monthToggle) monthToggle.checked = false;
                const depositToggle = document.getElementById('deposit-toggle');
                if (depositToggle) depositToggle.checked = false;
            } else if (period === 'deposit') {
                const depositToggle = document.getElementById('deposit-toggle');
                if (depositToggle) depositToggle.checked = true;
                if (monthToggle) monthToggle.checked = false;
                if (yearToggle) yearToggle.checked = false;
            }
    };

    // Open add-card popup
    window.openAdd_card = function() {
        const addToggle = document.getElementById('add_card-toggle');
        if (addToggle) addToggle.checked = true;
        // close other popups
        const monthToggle = document.getElementById('subscribe-month-toggle');
        const yearToggle = document.getElementById('subscribe-year-toggle');
        if (monthToggle) monthToggle.checked = false;
        if (yearToggle) yearToggle.checked = false;
        const depositToggle = document.getElementById('deposit-toggle');
        if (depositToggle) depositToggle.checked = false;
    };

    // Submit add card via AJAX
    window.submitAddCard = function() {
        const numberEl = document.getElementById('card-number');
        const holderEl = document.getElementById('card-cardholder');
        const monthEl = document.getElementById('card-expiry-month');
        const yearEl = document.getElementById('card-expiry-year');
        const resultEl = document.getElementById('add-card-result');

        if (!numberEl || !monthEl || !yearEl) return;
        const number = (numberEl.value || '').replace(/\s+/g, '');
        const holder = holderEl ? holderEl.value : '';
        const month = monthEl.value;
        const year = yearEl.value;

        // enforce 13..16 digits allowed (max 16 digits). Client-side limit reduces chance of extra-digit input.
        if (number.length < 13 || number.length > 16 || !/^[0-9]+$/.test(number)) {
            if (resultEl) resultEl.textContent = cardMessages.invalid_card_number;
            return;
        }

        const csrfInput = document.querySelector('input[name="csrfmiddlewaretoken"]');
        const csrf = csrfInput ? csrfInput.value : '';

        const fd = new FormData();
        fd.append('card_number', number);
        fd.append('cardholder', holder);
        fd.append('expiry_month', month);
        fd.append('expiry_year', year);

        fetch('{% url "add-card" %}', {
            method: 'POST',
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': csrf,
            },
            body: fd,
        })
        .then(r => r.json())
        .then(data => {
            if (data.error) {
                if (resultEl) resultEl.textContent = data.error;
                return;
            }
            // rebuild cards list
            const cardsList = document.getElementById('cards-list');
            if (cardsList && data.cards) {
                let html = '<strong>' + cardMessages.cards_label + '</strong><div style="margin-top:6px;">';
                if (data.cards.length === 0) html += '<div class="card-item">' + cardMessages.no_cards + '</div>';
                data.cards.forEach(c => {
                    html += `<div class="card-item" style="margin-bottom:8px; padding-bottom:8px; border-bottom:1px solid #eee;">**** **** ****${c.last4} — ${c.cardholder || '-'} — ${c.expiry}</div>`;
                });
                html += '</div>';
                cardsList.innerHTML = html;
            }
            // close add card form
            const addToggle = document.getElementById('add_card-toggle');
            if (addToggle) addToggle.checked = false;
            if (resultEl) resultEl.textContent = cardMessages.card_added;
            // clear inputs
            if (numberEl) numberEl.value = '';
            if (holderEl) holderEl.value = '';
        })
        .catch(err => {
            console.error('Add card failed', err);
            if (resultEl) resultEl.textContent = cardMessages.add_card_failed;
        });
    };

    const sideMenuLinks = document.querySelectorAll('.side-menu label, .side-menu a');
    sideMenuLinks.forEach(link => {
        link.addEventListener('click', () => {
            const menuToggle = document.getElementById('menu-toggle');
            if(menuToggle) menuToggle.checked = false;
        });
    });

    const formCheckboxes = ['profile-toggle', 'setting-toggle', 'form1-toggle', 'form2-toggle', 'subscribe-month-toggle', 'subscribe-year-toggle', 'deposit', 'add_card'];
    formCheckboxes.forEach(id => {
        const cb = document.getElementById(id);
        if(cb) {
            cb.addEventListener('change', () => {
                if(cb.checked) {
                    formCheckboxes.forEach(otherId => {
                        if(otherId !== id) {
                            const otherCb = document.getElementById(otherId);
                            if(otherCb) otherCb.checked = false;
                        }
                    });
                }
            });
        }
    });

    const walletForm = document.querySelector('.wallet form');
    if (walletForm) {
        walletForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const formData = new FormData(walletForm);
            const csrf = formData.get('csrfmiddlewaretoken');

            fetch(walletForm.action, {
                method: 'POST',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': csrf,
                },
                body: formData,
            })
            .then(resp => {
                if (!resp.ok) throw new Error('Network response was not ok');
                return resp.json();
            })
            .then(data => {
                if (data && data.price_converted) {
                    const el = document.getElementById('wallet-amount');
                    if (el) el.textContent = 'Wallet: ' + data.price_converted;
                    const depositWallet = document.getElementById('deposit-wallet');
                    if (depositWallet) depositWallet.textContent = data.price_converted;
                    updateDepositResult();
                }
            })
            .catch(err => console.error('Currency change failed:', err));
        });
    }
});