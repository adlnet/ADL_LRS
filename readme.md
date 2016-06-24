# ADL LRS Ansible & Vagrant Documentation

This document outlines how to get the ADL LRS installed locally using
Vagrant as well as how to deploy it to a remote server using Ansible.


## Prerequisites

### Ansible
Both local and remote installations require the installation of
[Ansible](https://www.ansible.com/get-started). You will want it install
in your local python environment.

  ```
  $ pip install -r requirements_ansible.txt
  ```

## Configure
This Ansible project has many default values set, but you may want to take a moment to configure your installation for your own needs.

You will find the primary default values in ``ansible/group_vars/all``.
Additional defaults can be found in the ``defaults/main.yml`` file
located within each ``ansible/roles/`` subdirectory.

To override these values, locally simply copy ``ansible/password.yml.tmpl`` to
``ansible/password.yml``. Update and/or override the variables here and they will
not be checked into source control.


## Local Vagrant Installation

This default configuration installs deploys the ADL LRS project to an Ubuntu 14.04 amd64 server.

### Prerequisites

#### Virtualbox

Install [Virtualbox](https://www.virtualbox.org/wiki/Downloads)

#### Vagrant

Install [Vagrant](https://www.vagrantup.com/downloads.html)


### Provisioning and Installation

You can begin the provisioning and installation process by issuing the
following command:

    ```
    $ vagrant up
    ```

**Note** If you run into issues with guest additions during ``vagrant up`` running the following command will install a vagrant plugin that will update the necessary guest files:
``vagrant plugin install vagrant-vbguest``

You can now access the server via:

    ```
    $ vagrant ssh
    ```

### Starting the Server

    ```
    vagrant ssh
    $ python manage.py createsuperuser
    $ python manage.py runserver 0.0.0.0:8000
    ```

### Destroy the Server

    ```
    $ vagrant destroy
    ```

## Remote Installations

**NOTE** This process will install ADL LRS on a server by means of nginx + uwsgi.
**THE RESULTING INSTALLATION IS NOT SECURED**

### Prerequisites

This method assumes you have created an Ubuntu server and have root access.

### Configuration
#### Inventory

The inventory file specifies the server to which you will be connecting.

You can use the example inventory as a template. Copy ``ansible/inventory_example.yml`` to ``ansible/dev.yml`` and edit the values to reflect your server and credentials.

### Installation

  ```
  $ ansible-playbook --private-key=<private_key_file> -K -i <inventory_file> deploy.yml
  ```

This command will run the ``deploy.yml`` script on the servers specified
in ``<inventory_file>``. You can specify a non-default ssh key using
``--private-key`` if necessary. The ``-K`` flag will prompt you for your
sudo password.


### Starting the Server

The server and its services should now be running and accessible at the
domain you specified during installation.

Connect to your server via ssh and create your superuser account. The
example code below may vary based on your configuration values:

    ```
    $ sudo su - lrs
    $ . ~/.virtualenvs/lrs/bin/activate
    (lrs) $ cd ~/ADL_LRS
    (lrs) $ python manage.py createsuperuser
    ```
