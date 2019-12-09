$(function () {
    $('ul.nav .nav-item a').each(function () {
        if($(this).attr("href") === window.location.pathname){
            $(this).addClass('active');
        }
    });
})