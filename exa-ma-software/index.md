# WP7 : HPC Resources for Exa-MA
v1.0, 2023-06-19
:doctype: book
:title-page:
:sectnums:
:toc: left
:toclevels: 2
:icons: font
:icon-set: fab
:imagedir: 

{author} -- version {revnumber}, {revdate}

## Work Package 7

Work Package 7 (WP7) in the Exa-MA project focuses on several key objectives. Firstly, it involves software development ranging from basic to advanced testing, including benchmarking, to verify the capabilities of exascale computing and address identified challenges. The aim is to deliver software packages following the continuous integration/continuous delivery (CI/CD) framework proposed by ExaDIP.

Secondly, WP7 coordinates co-design activities within Exa-MA, working closely with the ExaDIP project. This collaboration ensures effective communication and synergy between the projects to drive advancements in exascale computing.

Additionally, WP7 aims to establish a showroom to showcase the results achieved through Exa-MA. This showroom will serve as a platform to present and highlight the outcomes and achievements of the project.

Lastly, WP7 contributes to the creation of training material based on the results of Exa-MA. The insights gained from the project will be leveraged to develop educational resources and materials, facilitating knowledge transfer and dissemination.

To accomplish these objectives, WP7 relies on the principles of non-regression, verification, and validation. The various studies and developments conducted across different work packages within Exa-MA will undergo rigorous testing and evaluation before integration into a demonstrator.

WP7 is staffed by a dedicated team of engineers who work at the intersection of Exa-MA and other projects, particularly ExaDIP. The management of WP7 follows an Agile approach, aligning with the project management plan established in WP0 to ensure efficient and effective progress towards the set goals.

### Testing Process sub objectives

Here are the objectives for the testing process of  software in the Exa-MA Project, "Methods and Algorithms for Exascale Computing":

* **Build a Global Testing Process**
* Define a coherent structure for all demonstrators within Work Package 1 (WPto ensure consistency and alignment.
* Establish a common measurement system to enable standardized evaluation and comparison of different demonstrator components.
* **Ensure Demonstrator Non-Regression**
* Maintain a consolidated solution over time, unless there is a unanimously accepted justification for making changes.
* Guarantee that the existing demonstrator functionalities do not regress or deteriorate during updates or modifications.
* **Ensure Non-Regression of New Developments**
* Guarantee that new developments integrated into the demonstrator do not introduce regression or adverse effects.
* Test and validate new developments to ensure they maintain or enhance the existing functionality and performance of the demonstrator.
* **Validate Method Applicability in a Wider Context**
* Ensure that the developed method is not only effective on its own but also works well within a broader context of use.
* Evaluate the method’s performance and compatibility when coupled with other functionalities or integrated into a larger system.
* **Ensure Long-Term Contribution of the New Method**
* Guarantee the sustainability and continuous improvement of the new method over time.
* Monitor its performance, reliability, and relevance to ensure it remains valuable and beneficial in the evolving landscape of exascale computing.
* **Provide Interpretable Benefits of New Methods**
* Establish a simple and intuitive way of interpreting and quantifying the advantages and benefits of the newly developed methods.
* Develop metrics or measures that clearly demonstrate the positive impact and value of the new methods compared to previous approaches.

By aligning our software development and testing processes with these objectives, we can ensure the reliability, non-regression, and continuous improvement of the demonstrator while providing meaningful insights into the benefits and contributions of the new methods in the context of exascale computing.

Here are the process tests that we want to set up for the Exa-MA Project:

* **Non-Regression Process**
* Objective:: We want to guarantee that the result obtained remains identical to the original result, in a bit-by-bit sense, for options unaffected by proposed software evolutions.
* Test Case:: Our focus will be on a simple part of the software sources, falling into the category of elementary tests.
* Purpose:: We aim to ensure that the proposed software changes do not introduce any unintended regressions or alterations in the expected results.
* **Verification Process**
* Objective:: We aim to measure the absence of drift in consolidated solutions at a specific time (t), resulting from algorithmic optimization or improvement.
* Test Case:: The test case can be either elementary or integrated of order impacting a few additional software sources.
* Acceptance Criteria:: We will define acceptable relative variation thresholds for the solution obtained.
* Purpose:: Our goal is to verify that the algorithmic changes or optimizations do not cause unintended drift or significant changes in the consolidated solutions.
* **Validation Process**
* Objective:: We want to evaluate the performance of the proposed algorithm in a real-life configuration.
* Test Case:: The test case will be representative of the objective physics of the demonstrator or a mathematical equivalent if the demonstrator is not available.
* Integrated Validation Cases:: We will develop and implement validation cases that closely mimic the expected use cases and scenarios.
* Criteria for Measurement:: We will define criteria and metrics for measuring the method’s contribution and effectiveness.
* Purpose:: Our aim is to assess the algorithm’s performance and validate its suitability in real-life scenarios, ensuring it contributes meaningfully to the overall objectives of the demonstrator.

These process tests cover different aspects of testing and verification, ranging from ensuring non-regression and absence of drift to evaluating the algorithm’s performance in representative scenarios. By implementing these tests, we can validate the software changes, maintain stability, and measure the effectiveness of the proposed algorithms within the Exa-MA Project.

We propose the following workflow building on the [CI/CD framework](#ci/cd-). 
This workflow is based on the following principles:

**Exa-MA software development workflow**

![{imagedir}wp7-workflow]({imagedir}wp7-workflow.png)

### Demonstrator

For the Exa-MA Project, we have defined three levels of demonstrators.

* **Demonstrator Overview**
* Each relevant demonstrator should be listed in the demonstrator table.
* The table should include the demonstrator’s name, brief description, scientific barriers that exascale could overcome, any embedded software, challenges faced by the demonstrator, and the "bottlenecks" identified (such as memory, algorithms, data management, etc.). It should also specify the associated Work Package(s) (WP) for each demonstrator.
* **Tests for Demonstrators**
* Each demonstrator must define its own list of tests.
* The test list should include the name of the test, the type of test (non-regression, verification, or validation), the type of computer used (CPU, GPU, etc.), and the definition of test outputs.
* Standards should be established for deviations from expected outputs.
* Test execution should provide observables indicating whether the test passed or failed.
* **Mini-Apps and Proxy-Apps as Demonstrators**
* Level 1 Demonstrator:: A mini-app that covers one or two Exa-MA Work Packages. It focuses on specific objectives within those Work Packages.
* Level 2 Demonstrator:: A mini-app that covers two or more Exa-MA Work Packages. It demonstrates cross-collaboration and integration between multiple Work Packages.
* Level 3 Demonstrator:: A proxy-app that covers at least three Work Packages, potentially encompassing all Work Packages within Exa-MA. It serves as a representative workload for evaluating and optimizing the performance of high-performance computing systems.

**📌 NOTE**\
mini-apps and proxy-apps are defined [here](#mini-apps-and-proxy-apps).

By categorizing the demonstrators into different levels and considering Level 3 as proxy-apps, we can effectively track and evaluate their progress, ensuring they contribute to the objectives of the Exa-MA Project.

**Demonstrator Table**

| Demonstrator Name | Brief Description | Scientific Barriers | Embedded Software | Challenges | Bottlenecks | WP Concerned |
| --- | --- | --- | --- | --- | --- | --- |
| Level 1 Demonstrator |  |  |  |  |  |  |
|  |  |  |  |  |  |  |
| Level 2 Demonstrator |  |  |  |  |  |  |
|  |  |  |  |  |  |  |
| Level 3 Demonstrator |  |  |  |  |  |  |
|  |  |  |  |  |  |  |

For each demonstrator, we will define a list of tests with the following information:

**Demonstrator Tests**

| Test Name | Test Type | Computer Type | Test Outputs | Standards |
| --- | --- | --- | --- | --- |
| Level 1 Demonstrator |  |  |  |  |
|  |  |  |  |  |
| Level 2 Demonstrator |  |  |  |  |
|  |  |  |  |  |
| Level 3 Demonstrator |  |  |  |  |
|  |  |  |  |  |

Please fill in the table with the relevant information for each demonstrator and its associated tests.

## Estimates

### Level 1 demonstrators

A computing ressources form is available [here](https://forms.gle/iBs6YNgb8ZXCLk8L6).
We are gathering requests to get first estimates of our needs.

**Work Package Estimates (Level 1)**

|     |     |
| --- | --- |
| Work Package | Core Hours Estimate |
| Discretization | 500,000 |
| Model Order Reduction and ML | 1,000,000 |
| Solvers | 750,000 |
| Inverse Problems and Data Assim. | 1,500,000 |
| Optimization | 600,000 |
| Uncertainty Quantification | 900,000 |
| ***Total*** | 4,250,000 |

## Concepts for HPC

### CI/CD 

Continuous Integration/Continuous Delivery/Continuous Deployment (CI/CD/CD or simply CI/CD) strategies can be adapted and applied to high-performance computing (HPC) projects, including our project targeting exascale computing. While CI/CD is traditionally associated with software development and deployment, it can also be beneficial in managing the software and workflows associated with our HPC applications. Here are some considerations for implementing a CI/CD strategy for HPC exascale computing:

* **Version Control**\
We will utilize a version control system (e.g., Git) to manage our HPC application’s source code, scripts, and configuration files. This enables collaboration, tracks changes, and provides a history of our project.
* **Automated Builds**\
We will implement automated build processes to compile and build our HPC application from source code. This ensures that the application is built consistently and reproducibly across different environments.
* **Testing and Validation**\
We will develop a suite of automated tests to validate the correctness and functionality of our HPC application. This can include unit tests, integration tests, and performance tests. The tests should cover critical components and functionalities, and their execution should be automated as part of our CI/CD pipeline.
* **Continuous Integration**\
We will set up a CI server (e.g., Jenkins, GitLab CI) that automatically builds, tests, and validates our HPC application whenever changes are pushed to the version control system. This allows us to catch errors and issues early in the development process.
* **Artifact Management**\
We will store build artifacts, such as executables and libraries, in a central repository. This facilitates the deployment and distribution of our HPC application to different systems and environments.
* **Configuration Management**\
We will use configuration management tools (e.g., Ansible, Puppet) to manage the configuration and deployment of our HPC application on various computing resources. This includes managing dependencies, environment variables, and system configurations.
* **Continuous Deployment**\
We will automate the deployment of our HPC application to target systems, such as supercomputers or HPC clusters, as part of our CI/CD pipeline. This ensures that the latest version of our application is readily available for execution.
* **Monitoring and Logging**\
We will incorporate monitoring and logging mechanisms into our HPC application to collect performance metrics, diagnose issues, and track execution progress. This helps in identifying performance bottlenecks and troubleshooting any problems that arise during runtime.
* **Rollback and Rollforward**\
We will establish mechanisms for rolling back to a previous version of our HPC application in case of issues or failures. Additionally, we will enable the ability to roll forward to newer versions seamlessly, ensuring smooth upgrades and updates.
* **Collaboration and Documentation**\
We will encourage collaboration within the development team by providing clear documentation on the CI/CD processes, workflows, and best practices. This helps ensure consistency across the team and facilitates knowledge sharing.

It’s worth noting that the implementation details of a CI/CD strategy for HPC exascale computing may vary based on the specific requirements and constraints of our project. Considerations such as scalability, performance optimizations, and job scheduling on large-scale systems will play a significant role.

Adapting CI/CD practices to HPC can help streamline development, improve quality, and enhance the efficiency of our exascale computing project. It promotes automation, reproducibility, and collaboration, ultimately leading to more robust and reliable HPC applications.

### Containers

Containerization technologies like Docker and Singularity can play a valuable role in HPC environments, including exascale computing. They provide a way to package applications and their dependencies into portable and isolated containers, enabling consistent and reproducible execution across different computing systems. Here’s how we can utilize Docker and Singularity in our HPC CI/CD strategies:

* **Reproducible Environments**\
Containers allow us to create reproducible software environments by encapsulating the entire application stack, including the operating system, libraries, and dependencies. This ensures that our HPC applications run consistently regardless of the underlying host system.
* **Dependency Management**\
With Docker and Singularity, we can define and manage dependencies for our HPC applications within the container. This simplifies the process of ensuring that all required software components and libraries are available and properly configured, reducing compatibility issues.
* **Portability**\
Containers provide a portable execution environment that can be easily moved between different HPC systems, allowing our applications to run consistently across various computing resources. This is particularly useful in multi-site HPC environments or when collaborating with other researchers.
* **Isolation and Security**\
Containers offer a level of isolation, sandboxing our HPC applications from the host system and other containers. This enhances security and prevents conflicts between different applications or libraries.
* **Versioning and Rollback**\
Docker and Singularity enable versioning of containers, allowing us to maintain multiple versions of our HPC applications. This facilitates easy rollback to a previous version in case of issues, ensuring reproducibility and stability.
* **Continuous Integration with Containers**\
We can incorporate containerization into our CI/CD pipeline by automating the creation, testing, and deployment of containers. This can include building containers from Dockerfiles or using Singularity build recipes. Containers can be built as part of the CI/CD process and automatically tested and deployed to the target HPC systems.
* **Collaboration and Sharing**\
Docker Hub and Singularity Hub provide platforms for sharing and distributing containerized applications. We can leverage these platforms to share our HPC applications and their containers with collaborators or the broader community, facilitating collaboration and reproducibility.
* **Singularity for HPC Environments**\
Singularity, in particular, is designed with HPC in mind and offers features specific to high-performance computing, such as seamless integration with resource managers (e.g., Slurm), support for GPU passthrough, and the ability to run containers as unprivileged users.

When using container technologies in HPC environments, it’s important to consider certain factors, such as the performance impact of running within a container, data access and storage requirements, and specific security considerations relevant to our project and the target HPC system.

By leveraging Docker and Singularity containers, we can enhance the portability, reproducibility, and manageability of our HPC applications in the context of a CI/CD strategy.

### Mini Apps and Proxy Apps

Here are small definitions for mini apps and proxy apps:

* **Mini Apps**\
Mini apps, short for "miniature applications," are small-scale software programs or simulations that focus on specific aspects or components of a larger application or system. They are designed to capture the essential computational patterns and performance characteristics of the larger application while being more manageable and easier to understand. Mini apps are typically used for benchmarking, performance analysis, and optimization of specific computational kernels or algorithms. They serve as representative workloads that help evaluate and optimize the performance of high-performance computing systems.
* **Proxy Apps**\
Proxy apps, also known as "proxy applications," are software programs or simulations that mimic the behavior and computational patterns of real-world applications, particularly those used in scientific and engineering domains. They are developed with the aim of providing a lightweight representation of the computational requirements and communication patterns found in full-scale applications. Proxy apps help assess and optimize the performance

### Bottlenecks in parallel computing

Limitations in parallel computing arise due to various factors such as CPU bound, latency bound, and memory bound scenarios. CPU bound limitations occur when the performance of a computation is restricted by the processing power of the CPU, hindering its ability to efficiently complete tasks. Latency bound limitations occur when delays in data transfer or communication between system components impact the overall performance. Memory bound limitations arise when the speed or capacity of the memory system becomes the bottleneck, resulting in slower execution of computations. Understanding these limitations is crucial for optimizing parallel computing systems and applications.

#### Memory bound

In the context of High-Performance Computing (HPC), "memory bound" refers to a situation where the performance of a computational task is limited by the speed or capacity of the computer’s memory system, rather than by the processing power of the central processing unit (CPU) or other computational resources.

When a computation is memory bound, it means that the CPU spends a significant amount of time waiting for data to be fetched from or written to memory. This can occur when the amount of data being processed exceeds the available memory capacity, causing frequent transfers between the CPU and the main memory or other levels of cache. The data transfer latency and bandwidth limitations of the memory subsystem can become the bottleneck in the overall computation, resulting in slower performance.

Several factors can contribute to a computation becoming memory bound:

* **Data size**\
When working with large datasets or complex simulations, the amount of data being processed may exceed the available memory. As a result, the CPU needs to access data from main memory more frequently, leading to performance degradation.
* **Data dependencies**\
In some computations, the order in which data is accessed or modified can create dependencies that limit parallelism. This can cause delays as the CPU must wait for the completion of memory operations before proceeding.
* **Memory access patterns**\
Certain memory access patterns, such as irregular or non-contiguous memory accesses, can result in poor cache utilization and increased memory latency. This can negatively impact performance and make the computation memory bound.
* **Memory bandwidth limitations**\
The memory subsystem has a finite bandwidth, which determines how quickly data can be transferred between the CPU and memory. If the computational task requires high data throughput, the memory bandwidth may become a limiting factor.

To address memory-bound scenarios, several optimization techniques can be employed. These include data locality optimizations, such as improving cache utilization and reducing data movement between memory levels, as well as algorithmic optimizations that minimize unnecessary memory accesses. Additionally, utilizing techniques like data compression, data blocking, and parallel I/O can help mitigate the impact of memory-bound operations and improve overall performance in HPC applications.

#### Latency bound 

In High-Performance Computing (HPC), "latency bound" refers to a situation where the performance of a computation is primarily limited by the time it takes for data to travel between different system components or nodes, rather than by the processing power of the CPU or other resources.

Latency refers to the delay or the amount of time it takes for data to travel from its source to its destination. In a latency-bound scenario, the overall performance of a computation is constrained by the time it takes to access or transfer data, resulting in delays and slower execution.

Several factors can contribute to a computation becoming latency bound:

* **Network communication**\
In distributed computing environments, where computations are performed across multiple nodes, communication between these nodes becomes crucial. If the latency of network communication is high, it can lead to delays in data transfers and synchronization, limiting the overall performance of the computation.
* **Disk I/O latency**\
When computations involve frequent reading from or writing to disk, the latency associated with disk I/O operations can become a limiting factor. High disk I/O latency can result in longer waiting times for data retrieval or storage, slowing down the computation.
* **Memory latency**\
The time it takes for the CPU to access data from main memory or different levels of cache can also impact the overall performance. If the memory latency is high, it can introduce delays in data retrieval, reducing the efficiency of the computation.
* **Synchronization and coordination**\
In parallel computing scenarios, where multiple threads or processes need to synchronize their operations or coordinate their activities, the latency associated with these synchronization mechanisms can affect the performance. If synchronization operations introduce significant delays, it can make the computation latency bound.

To address latency-bound scenarios, several strategies can be employed:

* **Network optimization**\
Minimizing network latency by using high-speed, low-latency interconnects, optimizing network configurations, or utilizing network protocols that reduce communication overhead.
* **Disk I/O optimization**\
Employing techniques such as buffering, caching, or using faster storage devices (e.g., solid-state drives) to reduce disk I/O latency and improve overall performance.
* **Memory optimization**\
Optimizing data access patterns, improving cache utilization, and reducing unnecessary memory transfers to minimize memory latency and enhance performance.
* **Asynchronous operations**\
Utilizing asynchronous programming models and techniques to overlap computation and communication, reducing the impact of latency on overall performance.

It’s important to note that addressing latency-bound scenarios often involves a combination of hardware and software optimizations, as well as careful design considerations to minimize the impact of latency on the computation. The specific strategies employed will depend on the characteristics of the application, the communication patterns, and the underlying HPC system’s architecture.

#### CPU bound

In High-Performance Computing (HPC), "CPU bound" refers to a situation where the performance of a computational task is primarily limited by the processing power of the central processing unit (CPU), rather than by the speed or capacity of the memory system or other resources.

When a computation is CPU bound, it means that the CPU is the bottleneck, and it is fully utilized or heavily loaded, while other system resources such as memory, disk I/O, or network are not limiting factors. In such cases, the CPU spends most of its time executing instructions and performing calculations, and the overall performance of the computation is constrained by the CPU’s processing capabilities.

Several factors can contribute to a computation becoming CPU bound:

* **Computational complexity**\
If a computational task involves highly complex algorithms or calculations that require a significant amount of processing power, the CPU may become the limiting factor in achieving optimal performance.
* **Single-threaded execution**\
In some cases, a computation may rely on a single-threaded code that cannot be parallelized effectively. This means that the workload cannot be distributed across multiple CPU cores, leading to a situation where the CPU utilization is high, but the overall performance is limited by the single-threaded nature of the code.
* **Resource allocation**\
In multi-user or shared HPC environments, if multiple computational tasks are competing for CPU resources, it is possible for some tasks to be CPU bound if the available CPU capacity is insufficient to handle the workload effectively.
* **Insufficient parallelism**\
Even in situations where a computation can be parallelized, if the level of parallelism is not properly exploited or if there are dependencies that limit parallel execution, the computation may become CPU bound. In such cases, the CPU may not be fully utilized due to synchronization requirements or inefficient load balancing.

To address CPU-bound scenarios, various optimization techniques can be employed. These include:

* **Parallelization**\
Utilizing parallel programming models, such as Message Passing Interface (MPI) or OpenMP, to distribute the workload across multiple CPU cores or nodes, allowing for better utilization of available processing power.
* **Code optimization**\
Analyzing and optimizing the computational code to improve the efficiency of CPU utilization, such as reducing unnecessary computations, optimizing data access patterns, and exploiting vectorization or instruction-level parallelism.
* **Performance profiling**\
Profiling the application to identify performance bottlenecks and areas of the code where the CPU utilization can be improved. This can help identify areas for optimization and guide efforts to alleviate CPU-bound situations.

By addressing CPU-bound scenarios and optimizing the code and resource utilization, researchers and developers can improve the overall performance and efficiency of HPC applications, allowing them to achieve faster computation times and higher throughput.
