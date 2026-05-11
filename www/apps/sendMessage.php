<?php

require_once __DIR__ . '/mail_helper.php';

if (strpos($_SERVER['HTTP_USER_AGENT'], 'Googlebot') === false)
{
    $subject = "Paraglidable: direct message";
    $message = "Name: ". $_POST['name'] ."\nE-mail: ". $_POST['email'] ."\n---\nText: ". $_POST['text'];

    if (sendSmartMail("antoine.meler@gmail.com", $subject, $message, $_POST['email'])) {
        echo "1"; // OK
    } else {
        echo "Error";
    }
}

?>