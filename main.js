document.addEventListener("DOMContentLoaded", function () {

    // 1. Auto-hide flash messages after 5 seconds
    document.querySelectorAll(".flash").forEach(function (msg) {
        setTimeout(function () {
            msg.style.opacity = "0";
            setTimeout(function () { msg.remove(); }, 500);
        }, 5000);
    });

    // 2. Block past dates on the booking form
    var dateInput = document.querySelector('input[type="date"][name="date"]');
    if (dateInput) {
        var t = new Date();
        var mm = String(t.getMonth() + 1).padStart(2, "0");
        var dd = String(t.getDate()).padStart(2, "0");
        dateInput.min = t.getFullYear() + "-" + mm + "-" + dd;
    }

    // 3. Disable submit button after first click (prevents double submit)
    document.querySelectorAll("form").forEach(function (form) {
        form.addEventListener("submit", function () {
            var btn = form.querySelector('button[type="submit"]');
            if (btn) {
                btn.disabled = true;
                btn.textContent = "Please wait...";
            }
        });
    });

    // 4. Confirm before submitting a diagnosis
    var diagnoseForm = document.getElementById("diagnose-form");
    if (diagnoseForm) {
        diagnoseForm.addEventListener("submit", function (e) {
            if (!confirm("Submit this report? The patient will be notified.")) {
                e.preventDefault();
                var btn = diagnoseForm.querySelector('button[type="submit"]');
                btn.disabled = false;
                btn.textContent = "Submit Report";
            }
        });
    }
});