# -*- mode: ruby -*-
# vi: set ft=ruby :

VAGRANTFILE_API_VERSION = "2"

Vagrant.configure(VAGRANTFILE_API_VERSION) do |config|
  # Pick a base box
  config.vm.box = "trusty64"
  config.vm.box_url = "https://cloud-images.ubuntu.com/vagrant/trusty/20160621/trusty-server-cloudimg-amd64-vagrant-disk1.box"

  # Bump the memory to 1GB
  config.vm.provider "virtualbox" do |v|
    v.memory = 1024
  end

  # Forward guest OS port 8000 to Host OS port 8000 (on localhost)
  config.vm.network :forwarded_port, guest: 8000, host: 8000


  config.ssh.insert_key = false

  # Run the provisioning script
  config.vm.provision "ansible" do |ansible|
    ansible.verbose = "v"
    ansible.playbook = "ansible/vagrant.yml"
    ansible.extra_vars = {
      is_vagrant: true,
      REMOTE_USER: "vagrant",
      APP_USER: "vagrant",
      PROJECT_ROOT: "/vagrant/",
      server_name: "localhost"
    }
  end
end
