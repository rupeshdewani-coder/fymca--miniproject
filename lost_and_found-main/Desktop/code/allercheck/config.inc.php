<?php
/* phpMyAdmin configuration file */

// Servers configuration
$i = 0;

// The $cfg['Servers'] array starts with $cfg['Servers'][1]. Do not use $cfg['Servers'][0].
// You can disable a server config entry by setting host to ''.
$i++;

/* Authentication type */
$cfg['Servers'][$i]['auth_type'] = 'config';

/* Server parameters */
$cfg['Servers'][$i]['host'] = 'localhost';
$cfg['Servers'][$i]['port'] = '3306';
$cfg['Servers'][$i]['connect_type'] = 'tcp';
$cfg['Servers'][$i]['compress'] = false;
$cfg['Servers'][$i]['AllowNoPassword'] = true;

/* User credentials */
$cfg['Servers'][$i]['user'] = 'root';
$cfg['Servers'][$i]['password'] = '';

/* Directories for saving/loading files from server */
$cfg['UploadDir'] = '';
$cfg['SaveDir'] = '';

/* phpMyAdmin configuration */
$cfg['blowfish_secret'] = 'allercheck_secret_key_2025';

/* Basic settings */
$cfg['DefaultLang'] = 'en';
$cfg['DefaultCharset'] = 'utf8';
$cfg['VersionCheck'] = false;
$cfg['SendErrorReports'] = 'never';

/* Server verbose name */
$cfg['Servers'][$i]['verbose'] = 'allercheck MySQL Server';
?>