        if (getQueryVariable('forceDesktopMode') == '1' || getCookie('forceDesktopMode') == '1')
        {
            $('html > head').append($('<style>#popupMobileVersion {display:none;}</style>'));
            setCookie('forceDesktopMode', '1');
        }

        function stopAskingMobileVersion()
        {
            setCookie('forceDesktopMode', '1');
            $('#popupMobileVersion').css('display','none');
        }
    
