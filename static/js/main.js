document.addEventListener('DOMContentLoaded', function() {
    const fileInput = document.getElementById('phone_image');
    const previewContainer = document.getElementById('imagePreview');
    const previewImage = document.getElementById('preview');
    const removeButton = document.getElementById('removeImage');
    const fileUpload = document.querySelector('.file-upload');
    
    // Handle file selection
    fileInput.addEventListener('change', function() {
        const file = this.files[0];
        
        if (file) {
            const reader = new FileReader();
            
            reader.addEventListener('load', function() {
                previewImage.setAttribute('src', this.result);
                previewContainer.style.display = 'block';
                fileUpload.style.display = 'none';
            });
            
            reader.readAsDataURL(file);
        }
    });
    
    // Handle drag and drop
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        fileUpload.addEventListener(eventName, preventDefaults, false);
    });
    
    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }
    
    ['dragenter', 'dragover'].forEach(eventName => {
        fileUpload.addEventListener(eventName, highlight, false);
    });
    
    ['dragleave', 'drop'].forEach(eventName => {
        fileUpload.addEventListener(eventName, unhighlight, false);
    });
    
    function highlight() {
        fileUpload.classList.add('highlight');
    }
    
    function unhighlight() {
        fileUpload.classList.remove('highlight');
    }
    
    fileUpload.addEventListener('drop', handleDrop, false);
    
    function handleDrop(e) {
        const dt = e.dataTransfer;
        const file = dt.files[0];
        
        if (file) {
            fileInput.files = dt.files;
            
            const reader = new FileReader();
            
            reader.addEventListener('load', function() {
                previewImage.setAttribute('src', this.result);
                previewContainer.style.display = 'block';
                fileUpload.style.display = 'none';
            });
            
            reader.readAsDataURL(file);
        }
    }
    
    // Remove image
    removeButton.addEventListener('click', function() {
        fileInput.value = '';
        previewImage.setAttribute('src', '#');
        previewContainer.style.display = 'none';
        fileUpload.style.display = 'block';
    });
});