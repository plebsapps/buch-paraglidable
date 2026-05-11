<?php

include 'bdd.php';
require_once __DIR__ . '/../mail_helper.php'; // Ajout du helper

//=============================================================
// Verbose mode
//=============================================================


$verbose = false;

if ($verbose) {
	ini_set('display_errors',1);
	error_reporting(E_ALL);
}


//=============================================================
// Functions
//=============================================================


function generateRandomKey()
{
	$rndHex = substr(md5(rand()), 0, 16);
	$xorHex = 'ddb5097051cd211d';

	return dechex(hexdec($rndHex) ^ hexdec($xorHex));
}

//=============================================================
// Read params
//=============================================================


if ($verbose) {
	print_r($_GET);
}

$lst = array();

$email = filter_var($_GET["email"],  FILTER_VALIDATE_EMAIL);

if (!$email)
	die("ERROR: invalide email");

for ($i=0; true; $i++)
{
	if (array_key_exists("lat_$i",  $_GET) && 
		array_key_exists("lon_$i",  $_GET) && 
		array_key_exists("name_$i", $_GET)   )
	{
		array_push($lst, array( "lat"    => filter_var($_GET["lat_$i"],  FILTER_VALIDATE_FLOAT),
		 						"lon"    => filter_var($_GET["lon_$i"],  FILTER_VALIDATE_FLOAT),
								"name"   => $_GET["name_$i"],
								"spotId" => filter_var($_GET["spotId_$i"],  FILTER_VALIDATE_INT)  ) );
	}
	else
	{
		break;
	}
}

if ($verbose) {
	print_r($lst);
}


//=============================================================
// Insert into bdd
//=============================================================


$escaped_email = mysqli_real_escape_string($conn, $_GET['email']);

// Create account with email if does not exists
$sql = "INSERT INTO Accounts (email) VALUES ('". $escaped_email ."');";
executeQuery($conn, $sql, $verbose);

// Add/replace API key with a new random one
$apiKey          = generateRandomKey();
$sqlAccountQuery = "SELECT id FROM Accounts WHERE email='". $escaped_email ."'";
$latLonName      = mysqli_real_escape_string($conn, serialize($lst));
$sql = "REPLACE INTO ApiKeys (account, apiKey, latLonName) VALUES (($sqlAccountQuery), '$apiKey', '$latLonName');";
executeQuery($conn, $sql, $verbose);

if ($verbose) {
	print("key: $apiKey\n");
}


//=============================================================
// Send email with key
//=============================================================

$fromEmail = 'antoine@paraglidable.com';
$to      = $email;
$subject = "Paraglidable: your API key";

// Préparation du contenu (on sépare HTML et Texte brut)
$exampleUrlText = "https://api.paraglidable.com/?key=$apiKey&format=JSON&version=1\nhttps://api.paraglidable.com/?key=$apiKey&format=XML&version=1";
$exampleUrlHtml = "<a href=\"https://api.paraglidable.com/?key=$apiKey&format=JSON&version=1\">https://api.paraglidable.com/?key=$apiKey&format=JSON&version=1</a><br>".
                  "<a href=\"https://api.paraglidable.com/?key=$apiKey&format=XML&version=1\">https://api.paraglidable.com/?key=$apiKey&format=XML&version=1</a>";

// Version Texte Brut
$plainText = "Your API key is: $apiKey\n\nExamples:\n\n$exampleUrlText\n\nBest,\nAntoine";

// Version HTML
$htmlBody = "<html><body>Your API key is: <span style=\"font-weight:bold\">$apiKey</span><br><br>Examples:<br><br>$exampleUrlHtml<br><br>Best,<br>Antoine</body></html>";

// Appel de la fonction partagée
if (sendSmartMail($to, $subject, $htmlBody, $fromEmail, $plainText)) {
    echo "1"; // Succès
} else {
    echo "Error";
}

?>